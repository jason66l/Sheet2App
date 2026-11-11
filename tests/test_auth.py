"""Login-token checks, using a locally generated key instead of Supabase's."""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from backend.app import auth, config

URL = "https://example-project.supabase.co"
ISSUER = f"{URL}/auth/v1"


class _FakeJWKS:
    def __init__(self, public_key):
        self._key = public_key

    def get_signing_key_from_jwt(self, token):
        return type("SigningKey", (), {"key": self._key})()


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/test")
    config.get_settings.cache_clear()
    private = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(auth, "_jwks_client", lambda: _FakeJWKS(private.public_key()))
    yield private
    config.get_settings.cache_clear()


def _token(private, **overrides):
    claims = {
        "sub": "6f1c2a9e-1111-4c2b-9d1e-123456789abc",
        "email": "kai@example.com",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
        "user_metadata": {"full_name": "Kai Patel"},
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="ES256")


def test_valid_token_returns_user(key):
    user = auth.verify_token(_token(key))
    assert user.id == "6f1c2a9e-1111-4c2b-9d1e-123456789abc"
    assert user.email == "kai@example.com"
    assert user.name == "Kai Patel"


def test_expired_token_is_rejected(key):
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.verify_token(_token(key, exp=int(time.time()) - 10))


def test_token_from_another_project_is_rejected(key):
    with pytest.raises(jwt.InvalidIssuerError):
        auth.verify_token(_token(key, iss="https://someone-else.supabase.co/auth/v1"))


def test_token_signed_with_another_key_is_rejected(key):
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(jwt.InvalidSignatureError):
        auth.verify_token(_token(other))
