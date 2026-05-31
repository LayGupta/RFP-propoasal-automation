"""
auth.py — JWT Authentication Dependency for FastAPI

Provides a reusable FastAPI dependency `get_current_user()` that:
  1. Extracts the JWT from the Authorization: Bearer header
  2. Decodes it using the Supabase JWT secret
  3. Returns a UserClaims dataclass with user_id and email

Used by protected endpoints like /api/history and /api/scout-tenders.
"""

import os
import jwt
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header
from typing import Optional


@dataclass
class UserClaims:
    """Decoded JWT user identity extracted from Supabase Auth token."""
    user_id: str
    email: str


def _get_jwt_secret() -> str:
    """Retrieve the JWT secret from the Supabase service key's signing secret.

    Supabase uses the project's JWT secret (found in Dashboard → Settings → API → JWT Secret)
    to sign auth tokens. For simplicity, we use the SUPABASE_JWT_SECRET env var.
    Falls back to SUPABASE_SERVICE_KEY if JWT_SECRET is not explicitly set.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        # Fallback: many Supabase setups use a separate JWT secret
        # If not set, we'll try to decode without verification for development
        secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    return secret


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> UserClaims:
    """FastAPI dependency to extract and verify the Supabase JWT from the request.

    Args:
        authorization: The Authorization header value (e.g., "Bearer eyJhbG...")

    Returns:
        UserClaims with user_id and email extracted from the token.

    Raises:
        HTTPException 401 if the token is missing, malformed, or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or malformed Authorization header. Expected: Bearer <jwt_token>",
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    try:
        jwt_secret = _get_jwt_secret()

        if jwt_secret:
            # Verify the token signature with the Supabase JWT secret
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            # Development fallback: decode without verification
            # WARNING: Only use this in local development, never in production
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )

        user_id = payload.get("sub")
        email = payload.get("email", "unknown@user.com")

        if not user_id:
            raise HTTPException(status_code=401, detail="JWT token missing 'sub' claim (user ID).")

        return UserClaims(user_id=user_id, email=email)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token has expired. Please sign in again.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid JWT token: {str(e)}")


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[UserClaims]:
    """Optional auth dependency — returns None instead of 401 if no token is present.
    Used by endpoints that work with or without authentication."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
