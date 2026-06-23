"""
email_service.py — Gmail SMTP Email Dispatcher

Native Python smtplib + Gmail App Password.
Supports plain-text, HTML, and file attachment emails.

Setup:
  1. Enable 2FA on your Google account
  2. Generate an App Password at https://myaccount.google.com/apppasswords
  3. Set SMTP_USER and SMTP_PASSWORD in .env
"""

import smtplib
import logging
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, formatdate

from app.core.config import get_settings

logger = logging.getLogger("email_service")


class EmailError(Exception):
    """Raised when email dispatch fails after exhausting retries."""


def _build_base_message(
    to: str | list[str],
    subject: str,
    body: str,
    html: str | None = None,
) -> MIMEMultipart:
    """Build a MIME message with plain-text and optional HTML parts."""
    s = get_settings()
    recipients = [to] if isinstance(to, str) else to

    msg = MIMEMultipart("mixed")
    msg["From"] = formataddr(("FMCG Industrial Solutions", s.SMTP_USER))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Reply-To"] = s.SMTP_USER

    # Text alternatives sub-part
    text_part = MIMEMultipart("alternative")
    text_part.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        text_part.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(text_part)

    return msg


def _smtp_send(msg: MIMEMultipart, recipients: list[str]) -> None:
    """Authenticate and send via Gmail SMTP with STARTTLS."""
    s = get_settings()
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(s.SMTP_USER, s.SMTP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP authentication failed: %s", e)
        raise EmailError(
            "Gmail authentication failed. Check SMTP_USER and SMTP_PASSWORD "
            "(must be a 16-char App Password, not your account password)."
        ) from e
    except smtplib.SMTPRecipientsRefused as e:
        logger.error("All recipients refused: %s", e)
        raise EmailError(f"Recipient(s) refused: {recipients}") from e
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        raise EmailError(f"SMTP error: {e}") from e
    except TimeoutError as e:
        logger.error("SMTP connection timed out to %s:%d", s.SMTP_HOST, s.SMTP_PORT)
        raise EmailError(
            f"Connection to {s.SMTP_HOST}:{s.SMTP_PORT} timed out."
        ) from e
    except OSError as e:
        logger.error("Network error during SMTP: %s", e)
        raise EmailError(f"Network error: {e}") from e


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    html: str | None = None,
) -> bool:
    """Send a plain-text / HTML email via Gmail SMTP.

    Args:
        to: Recipient address or list of addresses.
        subject: Email subject line.
        body: Plain-text body (always included as fallback).
        html: Optional HTML body for rich formatting.

    Returns:
        True if sent successfully, False on failure.
    """
    s = get_settings()

    if not s.SMTP_USER or not s.SMTP_PASSWORD:
        logger.warning("SMTP_USER or SMTP_PASSWORD not configured, skipping email")
        return False

    recipients = [to] if isinstance(to, str) else to
    msg = _build_base_message(to=recipients, subject=subject, body=body, html=html)

    try:
        _smtp_send(msg, recipients)
        logger.info("Email sent to %s", recipients)
        return True
    except EmailError as e:
        logger.error("Failed to send email: %s", e)
        return False


def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    filename: str,
    mime_type: str = "application/octet-stream",
) -> None:
    """Send an email with a file attachment.

    Authenticates using the stored Gmail App Password and dispatches the
    email globally without restrictions.

    Args:
        to_email: Recipient email address (any domain — not restricted).
        subject: Email subject line.
        body: Plain-text email body.
        attachment_bytes: Raw file content as bytes.
        filename: Attachment filename (e.g. "RFP_Proposal_Highway.txt").
        mime_type: MIME type string (e.g. "text/plain", "application/pdf").

    Raises:
        EmailError: If SMTP credentials are missing or dispatch fails.
    """
    s = get_settings()

    # ── Validate SMTP credentials upfront ──
    if not s.SMTP_USER or not s.SMTP_PASSWORD:
        raise EmailError(
            "SMTP credentials not configured. "
            "Set SMTP_USER and SMTP_PASSWORD in your .env file."
        )

    if not to_email or "@" not in to_email:
        raise EmailError(f"Invalid recipient address: '{to_email}'")

    if not attachment_bytes:
        raise EmailError("Attachment is empty (0 bytes).")

    recipients = [to_email]

    # ── Build message with attachment ──
    msg = _build_base_message(to=recipients, subject=subject, body=body)

    # Attach file
    maintype, subtype = mime_type.split("/", 1) if "/" in mime_type else ("application", "octet-stream")
    file_part = MIMEBase(maintype, subtype)
    file_part.set_payload(attachment_bytes)
    encoders.encode_base64(file_part)
    file_part.add_header(
        "Content-Disposition",
        "attachment",
        filename=filename,
    )
    msg.attach(file_part)

    # ── Send ──
    _smtp_send(msg, recipients)
    logger.info(
        "Email sent to %s with attachment '%s' (%d bytes)",
        to_email,
        filename,
        len(attachment_bytes),
    )
