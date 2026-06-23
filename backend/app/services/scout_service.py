"""
scout_service.py — Proactive Tender Scouting via Tavily + ChatGroq

Scans product categories in the inventory database, searches for matching
tenders via Tavily web search, structures results with LLM, and dispatches
email alerts via Gmail SMTP.
"""

import json
import logging

from app.core.config import get_settings
from app.core.database import supabase_client
from app.services.email_service import send_email

logger = logging.getLogger("scout_service")


def _build_queries_from_inventory() -> list[dict]:
    """Build search queries from distinct product categories in the database."""
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

    seen: set[tuple] = set()
    queries = []
    for p in products:
        insulation = p.get("insulation_type", "XLPE")
        voltage = p.get("voltage_rating", 1100)
        material = p.get("conductor_material", "copper")
        key = (insulation, voltage, material)
        if key in seen:
            continue
        seen.add(key)
        query = f"{voltage}V {insulation} {material} cable tender RFP India 2025"
        label = f"{material.title()} {insulation} {voltage}V"
        queries.append({"query": query, "category": label})

    return queries[:5]


def _build_alert_html(opportunities: list[dict], categories: list[str]) -> str:
    """Build HTML email body for tender alert."""
    rows = ""
    for i, opp in enumerate(opportunities[:15], 1):
        rows += f"""
        <tr style="border-bottom:1px solid #e4e4e7;">
            <td style="padding:10px 12px;font-size:13px;color:#71717a;">{i}</td>
            <td style="padding:10px 12px;font-size:13px;font-weight:500;">
                <a href="{opp.get('source_url', '#')}" style="color:#3b82f6;text-decoration:none;">{opp.get('tender_title', 'Untitled')}</a>
            </td>
            <td style="padding:10px 12px;font-size:12px;color:#71717a;">{opp.get('issuing_authority', 'N/A')}</td>
            <td style="padding:10px 12px;font-size:12px;color:#52525b;">{opp.get('matched_category', 'General')}</td>
            <td style="padding:10px 12px;font-size:12px;color:#71717a;max-width:200px;">{opp.get('summary', '')[:120]}...</td>
        </tr>"""

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#3b82f6,#10b981);padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="color:white;margin:0;font-size:20px;">⚡ FMCG Tender Alert</h1>
            <p style="color:rgba(255,255,255,0.85);margin:4px 0 0 0;font-size:13px;">
                Auto-discovered {len(opportunities)} tender(s) across {len(categories)} product categories
            </p>
        </div>
        <div style="padding:20px;background:white;border:1px solid #e4e4e7;border-top:none;border-radius:0 0 12px 12px;">
            <p style="color:#52525b;font-size:13px;margin:0 0 16px 0;">
                Categories scanned: <strong>{', '.join(categories)}</strong>
            </p>
            <table style="width:100%;border-collapse:collapse;border:1px solid #e4e4e7;">
                <thead>
                    <tr style="background:#f4f4f5;">
                        <th style="padding:10px 12px;text-align:left;font-size:11px;color:#71717a;text-transform:uppercase;">#</th>
                        <th style="padding:10px 12px;text-align:left;font-size:11px;color:#71717a;text-transform:uppercase;">Tender</th>
                        <th style="padding:10px 12px;text-align:left;font-size:11px;color:#71717a;text-transform:uppercase;">Authority</th>
                        <th style="padding:10px 12px;text-align:left;font-size:11px;color:#71717a;text-transform:uppercase;">Category</th>
                        <th style="padding:10px 12px;text-align:left;font-size:11px;color:#71717a;text-transform:uppercase;">Summary</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="color:#a1a1aa;font-size:11px;margin-top:16px;">
                This alert was sent by the FMCG RFP Bid Intelligence Platform auto-scout system.
            </p>
        </div>
    </div>"""


def scout_and_alert() -> dict:
    """Execute a full inventory-wide tender scout and send email alert."""
    from langchain_groq import ChatGroq
    from langchain_community.tools.tavily_search import TavilySearchResults

    s = get_settings()
    alert_email = s.ALERT_EMAIL
    query_configs = _build_queries_from_inventory()
    categories = [q["category"] for q in query_configs]
    logger.info(f"Starting scout: {len(query_configs)} categories: {categories}")

    all_opportunities: list[dict] = []

    try:
        search_tool = TavilySearchResults(max_results=5, search_depth="advanced")
        scout_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        for qc in query_configs:
            query, category = qc["query"], qc["category"]
            logger.info(f"  Scouting: {category} → '{query}'")
            try:
                raw_results = search_tool.invoke(query)
                prompt = f"""You are a procurement intelligence analyst. Analyze these web search results about infrastructure tenders.

Search Results:
{json.dumps(raw_results, indent=2)}

Extract and return a JSON array of tender opportunities. Each object must have:
- "tender_title": string
- "summary": string (2-3 sentences)
- "issuing_authority": string
- "source_url": string

Return ONLY the raw JSON array. No explanation."""

                response = scout_llm.invoke(prompt)
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                try:
                    opps = json.loads(content)
                except json.JSONDecodeError:
                    opps = [
                        {"tender_title": r.get("title", "Unknown"), "summary": r.get("content", "")[:200],
                         "issuing_authority": "N/A", "source_url": r.get("url", "#")}
                        for r in raw_results[:3] if isinstance(r, dict)
                    ]
                for opp in opps:
                    opp["matched_category"] = category
                all_opportunities.extend(opps)
            except Exception as e:
                logger.error(f"  Scout failed for {category}: {e}")
                continue

        # Deduplicate
        seen_urls: set[str] = set()
        unique = []
        for opp in all_opportunities:
            url = opp.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique.append(opp)

        # Send alert
        alert_sent = False
        if unique and alert_email:
            html = _build_alert_html(unique, categories)
            plain = f"Found {len(unique)} tender(s) across {len(categories)} categories."
            alert_sent = send_email(
                to=alert_email,
                subject=f"[FMCG Alert] {len(unique)} New Tender(s) Across {len(categories)} Categories",
                body=plain,
                html=html,
            )

        # Log to database
        try:
            supabase_client.table("scout_logs").insert({
                "query": f"Inventory-wide: {', '.join(categories)}",
                "results_count": len(unique),
                "alert_sent": alert_sent,
                "results_json": json.dumps(unique),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log scout run: {e}")

        logger.info(f"Scout complete: {len(unique)} results, alert_sent={alert_sent}")
        return {
            "results_count": len(unique),
            "categories_searched": categories,
            "opportunities": unique,
            "alert_sent": alert_sent,
        }
    except Exception as e:
        logger.error(f"Scout failed: {e}")
        return {"results_count": 0, "categories_searched": categories, "opportunities": [], "alert_sent": False}
