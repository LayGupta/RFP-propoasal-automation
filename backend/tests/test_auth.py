"""test_auth.py — Auth endpoint tests"""

from unittest.mock import patch, MagicMock


def test_health_check(test_client):
    res = test_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["version"] == "3.0.0"


def test_register_success(test_client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-user"}]

    res = test_client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "securepass123", "full_name": "Test User",
    })
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_register_duplicate(test_client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": "existing"}]

    res = test_client.post("/api/auth/register", json={
        "email": "existing@example.com", "password": "pass123456", "full_name": "Existing",
    })
    assert res.status_code == 409


def test_login_missing_user(test_client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    res = test_client.post("/api/auth/login", json={
        "email": "noone@example.com", "password": "whatever123",
    })
    assert res.status_code == 401
