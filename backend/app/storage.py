"""File storage (Supabase Storage, private bucket "uploads").

Uses the secret key, so only the backend can read or write files. The frontend
never touches storage directly.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from backend.app.config import get_settings

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@lru_cache
def _client() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_secret_key)


def upload(path: str, data: bytes, content_type: str = XLSX_MIME) -> str:
    bucket = get_settings().storage_bucket
    _client().storage.from_(bucket).upload(path, data, {"content-type": content_type, "upsert": "false"})
    return path


def download(path: str) -> bytes:
    return _client().storage.from_(get_settings().storage_bucket).download(path)
