"""Who is calling? Verifies the Supabase login token sent by the frontend.

The frontend signs in with Google through Supabase and sends the resulting
access token as `Authorization: Bearer <token>`. Supabase signs those tokens
with a private key and publishes the matching public keys (a JWKS). We check
the signature against those public keys, so the backend stores no auth secret.
"""

from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.app.config import get_settings

bearer = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    id: str  # Supabase auth user id (UUID string)
    email: str | None = None
    name: str | None = None


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # Public keys are fetched once and cached by PyJWKClient.
    return jwt.PyJWKClient(f"{get_settings().auth_issuer}/.well-known/jwks.json", cache_keys=True)


def verify_token(token: str) -> AuthUser:
    """Raise jwt.PyJWTError if the token is invalid, expired or not ours."""
    settings = get_settings()
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=settings.auth_issuer,
    )
    meta = claims.get("user_metadata") or {}
    return AuthUser(
        id=claims["sub"],
        email=claims.get("email"),
        name=meta.get("full_name") or meta.get("name"),
    )


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> AuthUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    try:
        return verify_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid or expired token: {exc}") from exc
