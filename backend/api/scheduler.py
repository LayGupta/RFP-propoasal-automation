"""
scheduler.py — Proactive Cron-Based Tender Scouting with Email Alerts

Uses APScheduler to run a background job that:
  1. Searches for tenders via Tavily web search
  2. Uses ChatGroq to structure and score results
  3. Sends email alerts via Resend when high-relevance tenders are found
  4. Logs all scout runs to the scout_logs table

Default schedule: Daily at 6:00 AM IST (00:30 UTC)
"""

import os
import json
import logging
from datetime import datetime

import resend
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scout_scheduler")

# Module-level scheduler instance
scheduler = BackgroundScheduler()
_scheduler_started = False


def _get_scout_config() -> dict:
    """Read scout configuration from environment."""
    return {
        "query": os.environ.get("SCOUT_QUERY", "1100V XLPE cable tender RFP India"),
        "alert_email": os.environ.get("ALERT_EMAIL", ""),
        "resend_key": os.environ.get("RESEND_API_KEY", ""),
    }


def _send_alert_email(opportunities: list[dict], query: str, alert_email: str):
    """Send an email alert with discovered tender opportunities via Resend."""
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key or not alert_email:
        logger.warning("Resend key or alert email not configured, skipping email alert")
        return False

    resend.api_key = resend_key

    # Build HTML email body
    items_html = ""
    for opp in opportunities[:5]:
        items_html += f"""
        <div style="border:1px solid #e4e4e7; border-radius:8px; padding:16px; margin-bottom:12px; background:#fafafa;">
            <h3 style="margin:0 0 8px 0; color:#18181b; font-size:15px;">{opp.get('tender_title', 'Untitled')}</h3>
            <p style="margin:0 0 8px 0; color:#71717a; font-size:13px;">{opp.get('summary', 'No summary')}</p>
            <p style="margin:0; font-size:12px; color:#a1a1aa;">
                Issuing Authority: {opp.get('issuing_authority', 'N/A')} |
                <a href="{opp.get('source_url', '#')}" style="color:#3b82f6;">View Source</a>
            </p>
        </div>
        """

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width:600px; margin:0 auto;">
        <div style="background:linear-gradient(135deg, #3b82f6, #10b981); padding:24px; border-radius:12px 12px 0 0;">
            <h1 style="color:white; margin:0; font-size:20px;">⚡ FMCG Tender Alert</h1>
            <p style="color:rgba(255,255,255,0.85); margin:4px 0 0 0; font-size:13px;">
                Auto-discovered {len(opportunities)} new tender opportunity(ies)
            </p>
        </div>
        <div style="padding:20px; background:white; border:1px solid #e4e4e7; border-top:none; border-radius:0 0 12px 12px;">
            <p style="color:#52525b; font-size:13px; margin:0 0 16px 0;">
                Search query: <strong>"{query}"</strong>
            </p>
            {items_html}
            <div style="margin-top:20px; padding-top:16px; border-top:1px solid #e4e4e7;">
                <a href="http://localhost:5173" style="display:inline-block; background:#3b82f6; color:white; padding:10px 24px; border-radius:6px; text-decoration:none; font-size:14px; font-weight:600;">
                    Open RFP Platform
                </a>
            </div>
            <p style="color:#a1a1aa; font-size:11px; margin-top:16px;">
                This alert was sent by the FMCG RFP Bid Intelligence Platform auto-scout system.
            </p>
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "FMCG Tender Scout <onboarding@resend.dev>",
            "to": [alert_email],
            "subject": f"[FMCG Alert] {len(opportunities)} New Tender(s) Discovered",
            "html": html_body,
        })
        logger.info(f"Alert email sent to {alert_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def scout_and_alert():
    """Execute a tender scout run and send email alert if results found.
    
    This function is called by the scheduler on a cron schedule.
    It can also be called manually for testing.
    """
    from langchain_groq import ChatGroq
    from langchain_community.tools.tavily_search import TavilySearchResults
    from api.database.client import supabase_client

    config = _get_scout_config()
    query = config["query"]
    alert_email = config["alert_email"]

    logger.info(f"Starting auto-scout: query='{query}'")

    try:
        # Step 1: Tavily web search
        search_tool = TavilySearchResults(max_results=8, search_depth="advanced")
        raw_results = search_tool.invoke(query)

        # Step 2: LLM structuring
        scout_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        structuring_prompt = f"""You are a procurement intelligence analyst. Analyze these web search results about infrastructure tenders.

Search Results:
{json.dumps(raw_results, indent=2)}

Extract and return a JSON array of tender opportunities. Each object must have:
- "tender_title": string
- "summary": string (2-3 sentences)
- "issuing_authority": string
- "source_url": string

Return ONLY the raw JSON array."""

        response = scout_llm.invoke(structuring_prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            opportunities = json.loads(content)
        except json.JSONDecodeError:
            opportunities = [{"tender_title": r.get("title", "Unknown"), "summary": r.get("content", "")[:200], "issuing_authority": "N/A", "source_url": r.get("url", "#")} for r in raw_results[:5] if isinstance(r, dict)]

        # Step 3: Send email alert if results found
        alert_sent = False
        if opportunities and alert_email:
            alert_sent = _send_alert_email(opportunities, query, alert_email)

        # Step 4: Log to database
        try:
            supabase_client.table("scout_logs").insert({
                "query": query,
                "results_count": len(opportunities),
                "alert_sent": alert_sent,
                "results_json": json.dumps(opportunities),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log scout run: {e}")

        logger.info(f"Scout complete: {len(opportunities)} results, alert_sent={alert_sent}")
        return opportunities

    except Exception as e:
        logger.error(f"Scout failed: {e}")
        return []


def start_scheduler():
    """Start the background scheduler with the tender scout cron job."""
    global _scheduler_started
    if _scheduler_started:
        return

    # Daily at 6:00 AM IST = 00:30 UTC
    trigger = CronTrigger(hour=0, minute=30)
    scheduler.add_job(scout_and_alert, trigger, id="tender_scout", replace_existing=True)
    scheduler.start()
    _scheduler_started = True
    logger.info("Scout scheduler started (daily at 6:00 AM IST)")


def stop_scheduler():
    """Gracefully stop the background scheduler."""
    global _scheduler_started
    if _scheduler_started:
        scheduler.shutdown(wait=False)
        _scheduler_started = False
