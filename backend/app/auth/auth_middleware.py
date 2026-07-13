"""
auth/auth_middleware.py — FastAPI dependencies for authentication and roles.

Extracts the authenticated Identity (customer_id, email, role) from the
Bearer token on every protected request.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_utils import decode_access_token, TokenError
from app.auth.auth_service import Identity

_bearer = HTTPBearer(auto_error=False)

STAFF_ROLES = {"staff", "admin"}


def get_current_identity(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Identity:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    try:
        payload = decode_access_token(creds.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return Identity(
        customer_id=payload["sub"],     # was customer_unique_id
        email=payload["email"],
        role=payload["role"],
    )


def require_staff(
    identity: Identity = Depends(get_current_identity),
) -> Identity:
    if identity.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="staff or admin role required",
        )
    return identity
