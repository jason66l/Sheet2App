"""The only file that talks to an LLM provider.

Everything else calls generate_json(). Switching providers later means
rewriting this one file.
"""

from __future__ import annotations

import json
import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
log = logging.getLogger("sheet2app.ai")

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class LLMError(RuntimeError):
    pass


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60_000))


def generate_json(system: str, user: str, schema: dict, model: str | None = None) -> dict:
    """Ask the model for JSON matching `schema`. Returns the parsed dict.

    The caller still validates the result with Pydantic: the provider's schema
    support is a strong hint, not a guarantee.
    """
    model = model or DEFAULT_MODEL
    start = time.monotonic()
    resp = _client().models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,
        ),
    )
    usage = resp.usage_metadata
    log.info(
        "llm call model=%s in_tokens=%s out_tokens=%s seconds=%.1f",
        model,
        getattr(usage, "prompt_token_count", None),
        getattr(usage, "candidates_token_count", None),
        time.monotonic() - start,
    )
    if not resp.text:
        raise LLMError(f"empty response (finish reason: {resp.candidates[0].finish_reason if resp.candidates else 'none'})")
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError as e:
        raise LLMError(f"model returned invalid JSON: {e}") from e
