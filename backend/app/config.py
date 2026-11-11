"""Settings read from the environment (.env in the repo root).

Only the backend reads these. The secret key and database URL must never reach
the frontend or Git.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable {name}. Copy .env.example to .env and fill it in.")
    return value


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_secret_key: str
    database_url: str
    frontend_origins: list[str]
    storage_bucket: str = "uploads"
    max_upload_bytes: int = 25 * 1024 * 1024

    @property
    def auth_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
    return Settings(
        supabase_url=_required("SUPABASE_URL"),
        supabase_secret_key=_required("SUPABASE_SECRET_KEY"),
        database_url=_required("DATABASE_URL"),
        frontend_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
