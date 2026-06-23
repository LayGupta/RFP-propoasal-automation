"""
database.py — Supabase Client Singleton

Provides a single, lazily-initialised Supabase client that is safe to import
at module level and reuse across the entire application.

Usage:
    from app.core.database import supabase_client

    # or via the accessor (useful for testing / late binding)
    from app.core.database import get_supabase_client
    client = get_supabase_client()
"""

from __future__ import annotations

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client() -> Client:
    """
    Create and cache a Supabase client backed by the service-role key.

    The client is instantiated once per process (thanks to ``@lru_cache``) and
    reused for every subsequent call.  This avoids repeatedly negotiating new
    HTTP sessions while keeping the initialisation lazy — the client is only
    created when first requested.
    """
    settings = get_settings()

    client: Client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY,
    )
    logger.info(
        "Supabase client initialised for project: %s",
        settings.SUPABASE_URL.split("//")[1].split(".")[0],
    )
    return client


# ── Module-level convenience alias ────────────────────────────────────────────
# Backward-compatible: every file that does
#     from app.core.database import supabase_client
# will continue to work unchanged.
supabase_client: Client = get_supabase_client()
