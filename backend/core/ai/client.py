"""The only file that talks to an LLM provider.

Everything else calls generate_json(). Pick the provider in .env:

    LLM_PROVIDER=gemini              # default: Google AI Studio (GEMINI_API_KEY, GEMINI_MODEL)
    LLM_PROVIDER=openai_compatible   # any OpenAI-format API, e.g. Meta's Muse Spark:
    LLM_BASE_URL=https://...         #   the provider's base URL (ends in /v1)
    LLM_API_KEY=...                  #   that provider's key
    LLM_MODEL=muse-spark-1.3         #   the model id as that provider names it
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("sheet2app.ai")

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
DEFAULT_MODEL = (
    os.getenv("LLM_MODEL", "")
    if PROVIDER == "openai_compatible"
    else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
)
TIMEOUT_SECONDS = 120


class LLMError(RuntimeError):
    pass


# ------------------------------------------------------------------ Gemini


def _client() -> Any:
    """Gemini client. Callers must keep a reference while using it (it closes when garbage-collected)."""
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))


def _gemini(system: str, user: str, schema: dict | None, model: str) -> tuple[str, Any, Any]:
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=0,
    )
    if schema is not None:
        config.response_json_schema = schema
    client = _client()  # keep a reference so the connection isn't closed before the request
    resp = client.models.generate_content(model=model, contents=user, config=config)
    if not resp.text:
        reason = resp.candidates[0].finish_reason if resp.candidates else "none"
        raise LLMError(f"empty response (finish reason: {reason})")
    usage = resp.usage_metadata
    return resp.text, getattr(usage, "prompt_token_count", None), getattr(usage, "candidates_token_count", None)


# ------------------------------------------------- OpenAI-compatible (Muse Spark etc.)


def _openai_compatible(system: str, user: str, schema: dict | None, model: str) -> tuple[str, Any, Any]:
    from openai import OpenAI

    base_url, key = os.getenv("LLM_BASE_URL"), os.getenv("LLM_API_KEY")
    if not base_url or not key or not model:
        raise LLMError("LLM_PROVIDER=openai_compatible needs LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env.")
    client = OpenAI(base_url=base_url, api_key=key, timeout=TIMEOUT_SECONDS)
    # JSON mode ("return a JSON object"). The shape comes from the prompt; the caller validates it.
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    text = resp.choices[0].message.content if resp.choices else None
    if not text:
        raise LLMError(f"empty response (finish reason: {resp.choices[0].finish_reason if resp.choices else 'none'})")
    usage = resp.usage
    return text, getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None)


# ------------------------------------------------------------------ public


def _strip_fences(text: str) -> str:
    """Some models wrap JSON in ```json ... ``` even in JSON mode."""
    m = re.match(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", text, re.S)
    return m.group(1) if m else text


def generate_json(system: str, user: str, schema: dict | None = None, model: str | None = None) -> dict:
    """Ask the configured model for JSON. Returns the parsed dict.

    `schema` forces the output shape on Gemini only (slow for big schemas, so
    callers usually pass None and describe the shape in the prompt). The caller
    always validates the result with Pydantic.
    """
    model = model or DEFAULT_MODEL
    start = time.monotonic()
    call = _openai_compatible if PROVIDER == "openai_compatible" else _gemini
    text, tokens_in, tokens_out = call(system, user, schema, model)
    log.info(
        "llm call provider=%s model=%s in_tokens=%s out_tokens=%s seconds=%.1f",
        PROVIDER, model, tokens_in, tokens_out, time.monotonic() - start,
    )
    try:
        return json.loads(_strip_fences(text))
    except json.JSONDecodeError as e:
        raise LLMError(f"model returned invalid JSON: {e}") from e
