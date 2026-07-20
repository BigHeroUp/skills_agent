"""Dependency-light password hashing and signed API access tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    user_id: str
    tenant_id: str
    email: str
    role: str


class AuthService:
    def __init__(self, secret: str | None = None, token_ttl_seconds: int = 3600):
        configured = secret or os.getenv("PLATFORM_AUTH_SECRET", "")
        if os.getenv("PLATFORM_ENV", "development").lower() == "production" and len(configured) < 32:
            raise RuntimeError("PLATFORM_AUTH_SECRET must contain at least 32 characters in production")
        self.secret = configured.encode("utf-8")
        if len(self.secret) < 32:
            self.secret = hashlib.sha256(self.secret or b"local-development-only").digest()
        self.token_ttl_seconds = max(60, int(token_ttl_seconds))

    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 10:
            raise ValueError("Password must contain at least 10 characters")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, rounds, salt, expected = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), int(rounds)
            )
            return hmac.compare_digest(actual.hex(), expected)
        except (TypeError, ValueError):
            return False

    def issue_token(self, identity: Identity) -> str:
        payload = {
            "sub": identity.user_id,
            "tenant_id": identity.tenant_id,
            "email": identity.email,
            "role": identity.role,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.token_ttl_seconds,
        }
        body = self._encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = self._encode(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify_token(self, token: str) -> Identity:
        try:
            body, signature = token.split(".", 1)
            expected = self._encode(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid token signature")
            payload = json.loads(self._decode(body))
            if int(payload["exp"]) < int(time.time()):
                raise ValueError("Token expired")
            return Identity(
                user_id=str(payload["sub"]),
                tenant_id=str(payload["tenant_id"]),
                email=str(payload["email"]),
                role=str(payload["role"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid or expired access token") from exc

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
