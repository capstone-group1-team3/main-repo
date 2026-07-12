"""
auth/password_utils.py — password hashing and verification (bcrypt via passlib).

Passwords are never stored in plaintext; only the bcrypt hash lives on the
Account node in Neo4j.
"""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)
