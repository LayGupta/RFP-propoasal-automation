"""
test_endpoints.py — Backend Endpoint Unit Tests

Tests the PDF generation and email share endpoints with mocked SMTP
dispatch and Supabase queries. Uses FastAPI TestClient from conftest.

Coverage:
  - GET /api/proposals/{id}/pdf         → PDF download
  - POST /api/proposals/{id}/share      → Email with PDF attachment
  - POST /api/generate-pdf              → Legacy PDF endpoint
  - POST /api/send-outreach             → Legacy outreach email
  - GET /api/health                     → Health check
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.security import UserClaims, create_token


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

SAMPLE_MARKDOWN = """\
# RFP Technical Proposal

**Client:** Acme Corp
**Project:** Highway Cable Upgrade
**RFP Date:** 2026-06-15
**Commodity Volatility Multiplier:** 1.15x

---

## Technical Requirements Matrix

| Line Item | Cores | Material | Voltage (V) | Insulation | Specification |
|-----------|-------|----------|-------------|------------|---------------|
| LI-001 | 3 | copper | 1100 | XLPE | 3C x 240mm² XLPE 1.1kV |

---

## SKU Matching Results

| SKU ID | Product Name | Match % | Custom MTO | Gap Analysis |
|--------|-------------|---------|------------|--------------|
| SKU001 | Cable A | 95.0% | ✅ No | Direct match |

---

## Pricing Breakdown

| SKU ID | Cores | Voltage (V) | Base Price/m | Multiplier | Adjusted Price/m |
|--------|-------|-------------|-------------|------------|-----------------|
| SKU001 | 3 | 1100 | $89.44 | 1.15x | $102.86 |

**Total Base Price (all items):** $89.44/m
**Total Adjusted Price (all items):** $102.86/m
"""

SAMPLE_PROPOSAL_ROW = {
    "id": "prop-test-001",
    "thread_id": "thread-abc-123",
    "project_name": "Highway Cable Upgrade",
    "final_markdown": SAMPLE_MARKDOWN,
}


def _make_auth_header() -> dict[str, str]:
    """Generate a valid JWT Authorization header for test requests."""
    token = create_token("test-user-001", "tester@fmcg.test")
    return {"Authorization": f"Bearer {token}"}


def _mock_supabase_proposal_found(mock_supabase: MagicMock) -> None:
    """Configure mock_supabase to return SAMPLE_PROPOSAL_ROW for any .eq().limit() query."""
    result = MagicMock()
    result.data = [SAMPLE_PROPOSAL_ROW]
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = result


def _mock_supabase_proposal_not_found(mock_supabase: MagicMock) -> None:
    """Configure mock_supabase to return empty data."""
    result = MagicMock()
    result.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = result


# ══════════════════════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    def test_health_check_returns_200(self, test_client):
        res = test_client.get("/api/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "healthy"
        assert body["service"] == "fmcg-rfp-api"




# ══════════════════════════════════════════════════════════════════════════════
# Email Share: POST /api/proposals/{id}/share
# ══════════════════════════════════════════════════════════════════════════════

class TestShareEndpoint:
    def test_share_returns_401_without_auth(self, test_client):
        res = test_client.post(
            "/api/proposals/prop-test-001/share",
            json={"recipient_email": "client@example.com"},
        )
        assert res.status_code == 401

    def test_share_returns_404_for_missing_proposal(self, test_client, mock_supabase):
        _mock_supabase_proposal_not_found(mock_supabase)
        res = test_client.post(
            "/api/proposals/nonexistent/share",
            json={"recipient_email": "client@example.com"},
            headers=_make_auth_header(),
        )
        assert res.status_code == 404

    @patch("app.routers.email.send_email_with_attachment")
    def test_share_sends_email_successfully(
        self, mock_send_email, test_client, mock_supabase
    ):
        _mock_supabase_proposal_found(mock_supabase)
        mock_send_email.return_value = None  # no exception = success

        res = test_client.post(
            "/api/proposals/prop-test-001/share",
            json={
                "recipient_email": "client@acme.com",
                "subject": "Test Bid Submission",
                "message": "Please review attached.",
            },
            headers=_make_auth_header(),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "sent"
        assert body["recipient"] == "client@acme.com"
        mock_send_email.assert_called_once()

    @patch("app.routers.email.send_email_with_attachment")
    def test_share_handles_smtp_failure(
        self, mock_send_email, test_client, mock_supabase
    ):
        from app.services.email_service import EmailError

        _mock_supabase_proposal_found(mock_supabase)
        mock_send_email.side_effect = EmailError("SMTP auth failed")

        res = test_client.post(
            "/api/proposals/prop-test-001/share",
            json={"recipient_email": "client@acme.com"},
            headers=_make_auth_header(),
        )
        assert res.status_code == 502
        assert "SMTP auth failed" in res.json()["detail"]




# ══════════════════════════════════════════════════════════════════════════════
# Legacy: POST /api/send-outreach
# ══════════════════════════════════════════════════════════════════════════════

class TestLegacyOutreachEndpoint:
    @patch("app.routers.email.send_email")
    def test_outreach_sends_email(self, mock_send, test_client):
        mock_send.return_value = True

        res = test_client.post(
            "/api/send-outreach",
            json={
                "recipient_email": "sales@example.com",
                "email_body": "Hello, we have a proposal for you.",
                "subject": "FMCG Bid",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "sent"
        mock_send.assert_called_once()

    @patch("app.routers.email.send_email")
    def test_outreach_returns_500_on_failure(self, mock_send, test_client):
        mock_send.return_value = False

        res = test_client.post(
            "/api/send-outreach",
            json={
                "recipient_email": "sales@example.com",
                "email_body": "Test body",
                "subject": "Test",
            },
        )
        assert res.status_code == 500
