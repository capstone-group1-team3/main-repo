"""
auth/jwt_utils.py — encode / decode JWT access tokens.

Token payload carries: customer_id, email, role.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config.settings import settings


class TokenError(Exception):
    """Raised when a token is missing, expired, or otherwise invalid."""


def create_access_token(
    *,
    customer_id: str,       # was customer_unique_id
    email: str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    now    = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=expires_minutes or settings.jwt_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub":   customer_id,   # subject = stable customer key
        "email": email,
        "role":  role,
        "iat":   now,
        "exp":   expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid token") from exc
