"""
api/routes_auth.py — /auth/register, /auth/login, /auth/me endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.auth_service import (
    register, authenticate, authenticate_by_customer_id, AuthError, Identity,
)
from app.auth.auth_middleware import get_current_identity
from app.schemas.auth_schema import (
    RegisterRequest, LoginRequest, TokenResponse, IdentityResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=IdentityResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_endpoint(body: RegisterRequest):
    try:
        identity = register(
            email=body.email,
            password=body.password,
            customer_id=body.customer_id,   # was customer_unique_id
            role="customer",               # public registration is never privileged
        )
        return IdentityResponse(
            customer_id=identity.customer_id,
            email=identity.email,
            role=identity.role,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post("/login", response_model=TokenResponse)
def login_endpoint(body: LoginRequest):
    try:
        token = authenticate(body.email, body.password)
        return TokenResponse(access_token=token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


class CustomerLoginRequest(BaseModel):
    customer_id: str
    password: str


@router.post("/login/customer", response_model=TokenResponse)
def login_by_customer_id(body: CustomerLoginRequest):
    """
    Demo login: authenticate with customer_id + plain-text password.
    The backend hashes it and compares against the stored bcrypt hash.
    """
    try:
        token = authenticate_by_customer_id(
            body.customer_id, body.password
        )
        return TokenResponse(access_token=token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.get("/me", response_model=IdentityResponse)
def me_endpoint(identity: Identity = Depends(get_current_identity)):
    return IdentityResponse(
        customer_id=identity.customer_id,
        email=identity.email,
        role=identity.role,
    )
