"""
email router — Outreach & proposal sharing endpoints

Routes:
  POST /api/proposals/{id}/share   → fetch proposal, attach as .txt, email it
  POST /api/send-outreach          → plain-text outreach email
"""

import logging

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends

from app.core.security import UserClaims
from app.core.database import supabase_client
from app.routers.auth import get_current_user
from app.services.email_service import send_email, send_email_with_attachment, EmailError
from app.schemas.scout import SendEmailRequest

logger = logging.getLogger("email_router")

router = APIRouter(tags=["email"])


# ══════════════════════════════════════════════════════════════════════════════
# Request Schema
# ══════════════════════════════════════════════════════════════════════════════

class ShareProposalRequest(BaseModel):
    """Body for the /api/proposals/{id}/share endpoint."""
    recipient_email: str = Field(
        ...,
        description="Recipient email address (any domain).",
        examples=["client@example.com"],
    )
    subject: str = Field(
        default="FMCG Industrial Solutions — RFP Bid Proposal",
        description="Email subject line.",
    )
    message: str = Field(
        default="",
        description="Optional personal message to include in the email body.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/proposals/{id}/share
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/api/proposals/{proposal_id}/share")
async def share_proposal(
    proposal_id: str,
    request: ShareProposalRequest,
    user: UserClaims = Depends(get_current_user),
) -> dict:
    """
    Fetch a proposal by ID and email it as a .txt attachment.

    Path Parameters
    ---------------
    proposal_id : str
        The Supabase row ID of the proposal to share.

    Returns
    -------
    dict
        ``{"status": "sent", "recipient": "...", "proposal_id": "..."}``
    """
    # ── 1. Fetch proposal from Supabase ──
    try:
        result = (
            supabase_client.table("proposals")
            .select("id, thread_id, project_name, final_markdown")
            .or_(f"id.eq.{proposal_id},thread_id.eq.{proposal_id}")
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.exception("Database query failed for proposal=%s", proposal_id)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch proposal from database: {e}",
        )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Proposal '{proposal_id}' not found.",
        )

    proposal = result.data[0]
    markdown = proposal.get("final_markdown")

    if not markdown:
        raise HTTPException(
            status_code=422,
            detail="Proposal exists but has no markdown content to send.",
        )

    # ── 2. Build email body ──
    project_name = proposal.get("project_name", "RFP Proposal")
    sender_name = user.email.split("@")[0]

    body_lines = [
        f"Dear Recipient,",
        f"",
        f'Please find attached our technical proposal for "{project_name}".',
        f"",
    ]
    if request.message:
        body_lines.append(f"Note from {sender_name}:")
        body_lines.append(request.message)
        body_lines.append("")

    body_lines.extend([
        "This proposal includes:",
        "  • Technical requirements matrix",
        "  • SKU matching results with gap analysis",
        "  • Detailed pricing breakdown",
        "  • Engineering blueprints for custom MTO items (if applicable)",
        "",
        "We look forward to discussing this further.",
        "",
        "Best regards,",
        "FMCG Industrial Solutions",
        "IEC 60502 / IS 7098 Certified Manufacturer",
    ])

    body = "\n".join(body_lines)

    # ── 3. Prepare text file attachment ──
    txt_bytes = markdown.encode("utf-8")
    safe_name = "".join(
        c if c.isalnum() or c in "-_ " else "_" for c in project_name
    )[:50]
    filename = f"RFP_Proposal_{safe_name}.txt"

    # ── 4. Send email with text attachment ──
    try:
        send_email_with_attachment(
            to_email=request.recipient_email,
            subject=request.subject,
            body=body,
            attachment_bytes=txt_bytes,
            filename=filename,
            mime_type="text/plain",
        )
    except EmailError as e:
        logger.error(
            "Email dispatch failed: proposal=%s recipient=%s error=%s",
            proposal_id, request.recipient_email, e,
        )
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected email error for proposal=%s", proposal_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {e}",
        )

    logger.info(
        "Proposal shared: id=%s recipient=%s by=%s",
        proposal_id, request.recipient_email, user.email,
    )

    return {
        "status": "sent",
        "recipient": request.recipient_email,
        "proposal_id": proposal_id,
    }


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/send-outreach (legacy)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/api/send-outreach")
async def send_outreach(request: SendEmailRequest) -> dict:
    """Send a plain-text outreach email."""
    success = send_email(
        to=request.recipient_email,
        subject=request.subject,
        body=request.email_body,
    )
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Check SMTP_USER and SMTP_PASSWORD configuration.",
        )
    return {"status": "sent"}
