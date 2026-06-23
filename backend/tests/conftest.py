"""
conftest.py — Shared Pytest Fixtures

Provides:
  - mock_supabase: A fully-stubbed Supabase client mock
  - mock_auth_user: A pre-built UserClaims for authenticated endpoints
  - test_client: FastAPI TestClient with all external deps mocked
  - async event loop configuration for pytest-asyncio
"""

import asyncio
from typing import Generator

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.core.security import UserClaims


# ══════════════════════════════════════════════════════════════════════════════
# Async Event Loop (pytest-asyncio)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for pytest-asyncio tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ══════════════════════════════════════════════════════════════════════════════
# Mock Database Client
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def mock_supabase() -> MagicMock:
    """
    Patch Supabase client globally for the test session.

    Returns a MagicMock that mimics the supabase-py Client interface:
      - .table("x").select("*").execute()
      - .table("x").select("*").eq("col", val).execute()
      - .table("x").select("*").eq("col", val).limit(n).execute()
      - .table("x").select("*").eq("col", val).order("col").execute()
      - .table("x").select("*").order("col").limit(n).execute()
      - .table("x").insert({}).execute()
    """
    mock = MagicMock()

    # Default empty results for all query chains
    empty_result = MagicMock()
    empty_result.data = []

    insert_result = MagicMock()
    insert_result.data = [{"id": "test-id"}]

    # Wire up every common chain to return empty by default
    table = mock.table.return_value
    select = table.select.return_value
    select.execute.return_value = empty_result
    select.eq.return_value.execute.return_value = empty_result
    select.eq.return_value.limit.return_value.execute.return_value = empty_result
    select.eq.return_value.order.return_value.execute.return_value = empty_result
    select.order.return_value.execute.return_value = empty_result
    select.order.return_value.limit.return_value.execute.return_value = empty_result
    table.insert.return_value.execute.return_value = insert_result

    return mock


# ══════════════════════════════════════════════════════════════════════════════
# Mock Auth User
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_auth_user() -> UserClaims:
    """Return a test UserClaims used to bypass JWT auth in endpoint tests."""
    return UserClaims(user_id="test-user-001", email="tester@fmcg.test")


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI Test Client
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def test_client(mock_supabase) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI TestClient with all external dependencies mocked:
      - Supabase client
      - LangGraph workflow + checkpointer
      - APScheduler start/stop
    """
    with (
        patch("app.core.database.get_supabase_client", return_value=mock_supabase),
        patch("app.core.database.supabase_client", mock_supabase),
        patch("app.graph.workflow.rfp_workflow", MagicMock()),
        patch("app.graph.workflow.checkpointer", MagicMock()),
        patch("app.graph.workflow._connection_pool", MagicMock()),
        patch("app.services.scheduler.start_scheduler", MagicMock()),
        patch("app.services.scheduler.stop_scheduler", MagicMock()),
    ):
        from app.main import app
        client = TestClient(app)
        yield client
