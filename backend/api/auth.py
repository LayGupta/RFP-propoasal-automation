"""
auth.py — Custom JWT Authentication System

Replaces Supabase Auth with a self-managed auth system:
  1. register() — Creates a new user with bcrypt-hashed password in the `users` table
  2. login() — Verifies credentials and returns a signed JWT
  3. get_current_user() — FastAPI dependency to extract/verify JWT from Authorization header

JWT tokens are signed with the JWT_SECRET environment variable using HS256.
Passwords are hashed with bcrypt (cost factor 12).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

import jwt
import bcrypt
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field

from api.database.client import supabase_client


# ─── JWT Configuration ───
JWT_SECRET = os.environ.get("JWT_SECRET", "fallback_dev_secret_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72  # Token valid for 3 days


# ─── Pydantic Models for Auth Endpoints ───
class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field("", description="User's full name (optional)")


class LoginRequest(BaseModel):
    """Request body for user login."""
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class AuthResponse(BaseModel):
    """Response returned on successful login/register."""
    token: str
    user_id: str
    email: str
    full_name: str


@dataclass
class UserClaims:
    """Decoded JWT user identity."""
    user_id: str
    email: str


# ─── Password Hashing Utilities ───
def _hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with cost factor 12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ─── JWT Token Utilities ───
def _create_token(user_id: str, email: str) -> str:
    """Create a signed JWT token with user claims.

    Token payload:
      - sub: user UUID (standard JWT subject claim)
      - email: user's email address
      - iat: issued-at timestamp
      - exp: expiration timestamp (JWT_EXPIRY_HOURS from now)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ─── Core Auth Functions ───
def register_user(request: RegisterRequest) -> AuthResponse:
    """Register a new user account.

    1. Check if email already exists in the users table
    2. Hash the password with bcrypt
    3. Insert the new user record
    4. Return a signed JWT token
    """
    # Check for existing user
    existing = (
        supabase_client.table("users")
        .select("id")
        .eq("email", request.email.lower().strip())
        .execute()
    )
    if existing.data and len(existing.data) > 0:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Hash password and insert user
    password_hash = _hash_password(request.password)
    user_id = str(uuid.uuid4())

    supabase_client.table("users").insert({
        "id": user_id,
        "email": request.email.lower().strip(),
        "password_hash": password_hash,
        "full_name": request.full_name.strip(),
    }).execute()

    # Generate JWT
    token = _create_token(user_id, request.email.lower().strip())

    return AuthResponse(
        token=token,
        user_id=user_id,
        email=request.email.lower().strip(),
        full_name=request.full_name.strip(),
    )


def login_user(request: LoginRequest) -> AuthResponse:
    """Authenticate a user with email + password.

    1. Look up the user by email
    2. Verify the password against the stored bcrypt hash
    3. Return a signed JWT token
    """
    # Find user by email
    result = (
        supabase_client.table("users")
        .select("id, email, password_hash, full_name")
        .eq("email", request.email.lower().strip())
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = result.data[0]

    # Verify password
    if not _verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Generate JWT
    token = _create_token(user["id"], user["email"])

    return AuthResponse(
        token=token,
        user_id=user["id"],
        email=user["email"],
        full_name=user.get("full_name", ""),
    )


# ─── FastAPI Dependencies ───
async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> UserClaims:
    """FastAPI dependency: extract and verify JWT from Authorization header.

    Returns UserClaims with user_id and email.
    Raises HTTPException 401 if token is missing, expired, or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email", "unknown@user.com")

        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing user ID claim.")

        return UserClaims(user_id=user_id, email=email)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please sign in again.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[UserClaims]:
    """Optional auth dependency — returns None instead of 401 if no token present."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
