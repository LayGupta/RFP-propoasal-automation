"""auth router — /api/auth/* endpoints"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header

import jwt as pyjwt

from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.core.security import (
    UserClaims, hash_password, verify_password,
    create_token, decode_token, generate_user_id,
)
from app.core.database import supabase_client

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> AuthResponse:
    existing = supabase_client.table("users").select("id").eq("email", request.email.lower().strip()).execute()
    if existing.data and len(existing.data) > 0:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    pw_hash = hash_password(request.password)
    user_id = generate_user_id()

    supabase_client.table("users").insert({
        "id": user_id,
        "email": request.email.lower().strip(),
        "password_hash": pw_hash,
        "full_name": request.full_name.strip(),
    }).execute()

    token = create_token(user_id, request.email.lower().strip())
    return AuthResponse(
        token=token, user_id=user_id,
        email=request.email.lower().strip(),
        full_name=request.full_name.strip(),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    result = (
        supabase_client.table("users")
        .select("id, email, password_hash, full_name")
        .eq("email", request.email.lower().strip())
        .execute()
    )
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = result.data[0]
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_token(user["id"], user["email"])
    return AuthResponse(
        token=token, user_id=user["id"],
        email=user["email"], full_name=user.get("full_name", ""),
    )


# ── FastAPI Dependencies ──

async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> UserClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization.split("Bearer ", 1)[1].strip()
    try:
        return decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please sign in again.")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[UserClaims]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
