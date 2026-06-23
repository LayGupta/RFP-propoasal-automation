"""
security.py — JWT token utilities and password hashing

Extracted from the monolithic auth.py to be reusable across routers.
"""

import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import jwt
import bcrypt

from app.core.config import get_settings

_s = get_settings()


@dataclass
class UserClaims:
    """Decoded JWT user identity."""
    user_id: str
    email: str


# ── Password Hashing ──

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ──

def create_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=_s.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _s.JWT_SECRET, algorithm=_s.JWT_ALGORITHM)


def decode_token(token: str) -> UserClaims:
    """Decode and validate a JWT. Raises jwt.* exceptions on failure."""
    payload = jwt.decode(token, _s.JWT_SECRET, algorithms=[_s.JWT_ALGORITHM])
    user_id = payload.get("sub")
    email = payload.get("email", "unknown@user.com")
    if not user_id:
        raise jwt.InvalidTokenError("Token missing user ID claim.")
    return UserClaims(user_id=user_id, email=email)


def generate_user_id() -> str:
    return str(uuid.uuid4())
