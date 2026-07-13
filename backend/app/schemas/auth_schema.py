"""
schemas/auth_schema.py — Pydantic models for auth endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email:       EmailStr
    password:    str = Field(min_length=6)
    customer_id: str                          # was customer_unique_id


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class IdentityResponse(BaseModel):
    customer_id: str    # was customer_unique_id
    email:       EmailStr
    role:        str
