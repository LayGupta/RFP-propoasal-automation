"""
config.py — Centralised Pydantic Settings

Every environment variable the application touches is declared once here.
Validation runs at import time; a missing required var fails fast with a
diagnostic message instead of producing cryptic NoneType errors at runtime.
"""

from pathlib import Path
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables into system environment for SDK clients
env_path = Path(__file__).resolve().parents[3] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(
        ..., description="Supabase project REST URL (https://<ref>.supabase.co)"
    )
    SUPABASE_KEY: str = Field(
        ...,
        alias="SUPABASE_SERVICE_KEY",
        description="Supabase service-role key (elevated server-side access)",
    )
    DATABASE_URL: str = Field(
        default="",
        description="Direct PostgreSQL connection string for LangGraph checkpointer",
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str = Field(
        ..., description="HMAC secret for signing/verifying JWTs"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 72

    # ── Email (Gmail SMTP) ────────────────────────────────────────────────────
    SMTP_HOST: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (587 for STARTTLS, 465 for SSL)",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP login username (e.g. user@gmail.com)",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP login password or App Password",
    )

    # ── Scout ─────────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""
    ALERT_EMAIL: str = ""
    SCOUT_QUERY: str = "1100V XLPE cable tender RFP India"

    # ── Runtime ───────────────────────────────────────────────────────────────
    ENV: Literal["development", "staging", "production"] = "development"
    PORT: int = 8000
    FRONTEND_URL: str = Field(
        default="http://localhost:5173",
        description="The base URL of the deployed frontend (for CORS). E.g., https://fmcg-rfp.vercel.app"
    )

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("SUPABASE_URL")
    @classmethod
    def _validate_supabase_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return v.rstrip("/")

    @field_validator("SMTP_PORT")
    @classmethod
    def _validate_smtp_port(cls, v: int) -> int:
        if v not in (25, 465, 587, 2525):
            raise ValueError(f"Unexpected SMTP_PORT {v}; expected 25, 465, 587, or 2525")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton for the process lifetime)."""
    return Settings()
