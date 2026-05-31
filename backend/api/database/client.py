"""
client.py — Unified Database Access Layer

Two singleton exports:
  1. supabase_client — Supabase REST Client for table queries and vector RPC calls
  2. connection_pool — psycopg ConnectionPool for the LangGraph PostgresSaver checkpointer

Both are initialized at module import time and validated against environment variables.
If any required variable is missing, a RuntimeError is raised immediately with a
diagnostic message to prevent silent failures in serverless cold starts.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from psycopg_pool import ConnectionPool

# Load environment variables from the root .env file (for local development)
# In Vercel, env vars are injected by the platform so this is a no-op
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_env_path)


# ─── Environment variable extraction with explicit validation ───
# These variables must be set in .env or the Vercel project environment settings.

# SUPABASE_URL: The project's REST API base URL (e.g., "https://xxxx.supabase.co")
_supabase_url: str | None = os.environ.get("SUPABASE_URL")

# SUPABASE_SERVICE_KEY: The service_role secret key with elevated permissions for backend operations
_supabase_service_key: str | None = os.environ.get("SUPABASE_SERVICE_KEY")

# DATABASE_URL: Direct PostgreSQL connection URI for persistent LangGraph state checkpointing
_database_url: str | None = os.environ.get("DATABASE_URL")


# ─── Validation gate — halt startup if any credential is absent ───
# Failing fast here prevents cryptic NoneType errors deep inside node execution.
if not _supabase_url:
    raise RuntimeError(
        "SUPABASE_URL environment variable is not set. "
        "Set it to your Supabase project URL (e.g., https://xxxx.supabase.co). "
        "Find it at: Supabase Dashboard → Settings → API → Project URL."
    )

if not _supabase_service_key:
    raise RuntimeError(
        "SUPABASE_SERVICE_KEY environment variable is not set. "
        "Set it to your Supabase service_role secret key (starts with 'eyJ...'). "
        "Find it at: Supabase Dashboard → Settings → API → service_role secret."
    )

if not _database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it to your Supabase direct PostgreSQL connection string "
        "(e.g., postgresql://postgres.[user]:[password]@db.[ref].supabase.co:5432/postgres). "
        "Find it at: Supabase Dashboard → Settings → Database → Connection string (URI)."
    )


# ─── Supabase REST Client singleton ───
# Used by workflow nodes for table queries and vector similarity RPC calls.
# The service_role key grants full access to all tables without RLS restrictions.
supabase_client: Client = create_client(_supabase_url, _supabase_service_key)


# ─── PostgreSQL Connection Pool singleton ───
# Used exclusively by the LangGraph PostgresSaver checkpointer for persistent state storage.
# max_size=5 balances connection reuse with Supabase's default connection limits.
# autocommit=True is required by PostgresSaver for DDL operations and checkpoint writes.
connection_pool: ConnectionPool = ConnectionPool(
    conninfo=_database_url,
    max_size=5,
    kwargs={"autocommit": True},
)

# Export the raw database URL for use by workflow.py during PostgresSaver.setup()
database_url: str = _database_url
