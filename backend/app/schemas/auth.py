from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field("", description="User's full name (optional)")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    full_name: str
