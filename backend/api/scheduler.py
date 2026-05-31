"""
scheduler.py — Proactive Cron-Based Tender Scouting with Email Alerts

Scans across ALL product categories in the inventory database:
  1. Fetches distinct product types from the products table
  2. Builds targeted search queries for each category
  3. Searches for tenders via Tavily web search
  4. Uses ChatGroq to structure and score results
  5. Sends email alerts via Resend when high-relevance tenders are found
  6. Logs all scout runs to the scout_logs table

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


def _build_queries_from_inventory() -> list[dict]:
    """Build search queries from distinct product categories in the database.
    
    Groups products by (insulation_type, voltage_rating, conductor_material)
    and creates targeted tender search queries for each category.
    
    Returns list of {"query": str, "category": str} dicts.
    """
    from api.database.client import supabase_client

    try:
        result = supabase_client.table("products").select(
            "insulation_type, voltage_rating, conductor_material, category"
        ).execute()
        products = result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch products for query building: {e}")
        return [{"query": "1100V XLPE cable tender RFP India", "category": "Default"}]

    if not products:
        return [{"query": "1100V XLPE cable tender RFP India", "category": "Default"}]

    # Group by unique (insulation, voltage, material) combinations
    seen = set()
    queries = []
    for p in products:
        insulation = p.get("insulation_type", "XLPE")
        voltage = p.get("voltage_rating", 1100)
        material = p.get("conductor_material", "copper")
        category = p.get("category", "power_cable")

        key = (insulation, voltage, material)
        if key in seen:
            continue
        seen.add(key)

        query = f"{voltage}V {insulation} {material} cable tender RFP India 2025"
        label = f"{material.title()} {insulation} {voltage}V"
        queries.append({"query": query, "category": label})

    # Cap at 5 queries to stay within Tavily rate limits
    return queries[:5]


def _send_alert_email(opportunities: list[dict], queries_used: list[str], alert_email: str):
    """Send an email alert with discovered tender opportunities via Resend."""
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key or not alert_email:
        logger.warning("Resend key or alert email not configured, skipping email alert")
        return False

    resend.api_key = resend_key

    # Build HTML table rows
    rows_html = ""
    for i, opp in enumerate(opportunities[:15], 1):
        rows_html += f"""
        <tr style="border-bottom:1px solid #e4e4e7;">
            <td style="padding:10px 12px; font-size:13px; color:#71717a;">{i}</td>
            <td style="padding:10px 12px; font-size:13px; font-weight:500; color:#18181b;">
                <a href="{opp.get('source_url', '#')}" style="color:#3b82f6; text-decoration:none;">{opp.get('tender_title', 'Untitled')}</a>
            </td>
            <td style="padding:10px 12px; font-size:12px; color:#71717a;">{opp.get('issuing_authority', 'N/A')}</td>
            <td style="padding:10px 12px; font-size:12px; color:#52525b;">{opp.get('matched_category', 'General')}</td>
            <td style="padding:10px 12px; font-size:12px; color:#71717a; max-width:200px;">{opp.get('summary', '')[:120]}...</td>
        </tr>
        """

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width:800px; margin:0 auto;">
        <div style="background:linear-gradient(135deg, #3b82f6, #10b981); padding:24px; border-radius:12px 12px 0 0;">
            <h1 style="color:white; margin:0; font-size:20px;">⚡ FMCG Tender Alert</h1>
            <p style="color:rgba(255,255,255,0.85); margin:4px 0 0 0; font-size:13px;">
                Auto-discovered {len(opportunities)} tender(s) across {len(queries_used)} product categories
            </p>
        </div>
        <div style="padding:20px; background:white; border:1px solid #e4e4e7; border-top:none; border-radius:0 0 12px 12px;">
            <p style="color:#52525b; font-size:13px; margin:0 0 16px 0;">
                Categories scanned: <strong>{', '.join(queries_used)}</strong>
            </p>
            <table style="width:100%; border-collapse:collapse; border:1px solid #e4e4e7; border-radius:8px;">
                <thead>
                    <tr style="background:#f4f4f5;">
                        <th style="padding:10px 12px; text-align:left; font-size:11px; color:#71717a; text-transform:uppercase;">#</th>
                        <th style="padding:10px 12px; text-align:left; font-size:11px; color:#71717a; text-transform:uppercase;">Tender Title</th>
                        <th style="padding:10px 12px; text-align:left; font-size:11px; color:#71717a; text-transform:uppercase;">Authority</th>
                        <th style="padding:10px 12px; text-align:left; font-size:11px; color:#71717a; text-transform:uppercase;">Category</th>
                        <th style="padding:10px 12px; text-align:left; font-size:11px; color:#71717a; text-transform:uppercase;">Summary</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
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
            "subject": f"[FMCG Alert] {len(opportunities)} New Tender(s) Across {len(queries_used)} Categories",
            "html": html_body,
        })
        logger.info(f"Alert email sent to {alert_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def scout_and_alert():
    """Execute a full inventory-wide tender scout and send email alert.
    
    1. Builds queries from distinct product categories in the database
    2. Runs Tavily search for each category
    3. LLM structures raw results into tender opportunities
    4. Sends tabulated email alert
    5. Logs to scout_logs table
    """
    from langchain_groq import ChatGroq
    from langchain_community.tools.tavily_search import TavilySearchResults
    from api.database.client import supabase_client

    alert_email = os.environ.get("ALERT_EMAIL", "")

    # Step 1: Build queries from inventory categories
    query_configs = _build_queries_from_inventory()
    categories_searched = [q["category"] for q in query_configs]
    logger.info(f"Starting inventory-wide scout: {len(query_configs)} categories: {categories_searched}")

    all_opportunities = []

    try:
        search_tool = TavilySearchResults(max_results=5, search_depth="advanced")
        scout_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        for qc in query_configs:
            query = qc["query"]
            category = qc["category"]
            logger.info(f"  Scouting: {category} → '{query}'")

            try:
                # Tavily search
                raw_results = search_tool.invoke(query)

                # LLM structuring
                structuring_prompt = f"""You are a procurement intelligence analyst. Analyze these web search results about infrastructure tenders.

Search Results:
{json.dumps(raw_results, indent=2)}

Extract and return a JSON array of tender opportunities. Each object must have:
- "tender_title": string
- "summary": string (2-3 sentences)
- "issuing_authority": string
- "source_url": string

Return ONLY the raw JSON array. No explanation."""

                response = scout_llm.invoke(structuring_prompt)
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

                try:
                    opps = json.loads(content)
                except json.JSONDecodeError:
                    opps = [{"tender_title": r.get("title", "Unknown"), "summary": r.get("content", "")[:200], "issuing_authority": "N/A", "source_url": r.get("url", "#")} for r in raw_results[:3] if isinstance(r, dict)]

                # Tag each opportunity with the matched category
                for opp in opps:
                    opp["matched_category"] = category

                all_opportunities.extend(opps)

            except Exception as e:
                logger.error(f"  Scout failed for {category}: {e}")
                continue

        # Deduplicate by source_url
        seen_urls = set()
        unique_opportunities = []
        for opp in all_opportunities:
            url = opp.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_opportunities.append(opp)

        # Step 3: Send email alert if results found
        alert_sent = False
        if unique_opportunities and alert_email:
            alert_sent = _send_alert_email(unique_opportunities, categories_searched, alert_email)

        # Step 4: Log to database
        try:
            supabase_client.table("scout_logs").insert({
                "query": f"Inventory-wide: {', '.join(categories_searched)}",
                "results_count": len(unique_opportunities),
                "alert_sent": alert_sent,
                "results_json": json.dumps(unique_opportunities),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log scout run: {e}")

        logger.info(f"Scout complete: {len(unique_opportunities)} unique results across {len(categories_searched)} categories, alert_sent={alert_sent}")

        return {
            "results_count": len(unique_opportunities),
            "categories_searched": categories_searched,
            "opportunities": unique_opportunities,
            "alert_sent": alert_sent,
        }

    except Exception as e:
        logger.error(f"Scout failed: {e}")
        return {"results_count": 0, "categories_searched": categories_searched, "opportunities": [], "alert_sent": False}


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
