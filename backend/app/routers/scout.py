"""scout router — /api/scout-* endpoints"""

import os
import json
from fastapi import APIRouter, HTTPException

from app.schemas.scout import ScoutRequest
from app.services.scout_service import scout_and_alert

router = APIRouter(tags=["scout"])


@router.post("/api/scout-tenders")
async def scout_tenders(request: ScoutRequest) -> dict:
    from langchain_groq import ChatGroq
    from langchain_community.tools.tavily_search import TavilySearchResults

    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        raise HTTPException(status_code=500, detail="TAVILY_API_KEY not configured.")

    try:
        search_tool = TavilySearchResults(max_results=8, search_depth="advanced")
        raw_results = search_tool.invoke(request.query)

        scout_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        prompt = f"""You are a procurement intelligence analyst. Analyze the following web search results about infrastructure tenders and RFPs.

Search Results:
{json.dumps(raw_results, indent=2)}

Extract and return a JSON array of tender opportunities. Each object must have exactly these fields:
- "tender_title": string
- "summary": string (2-3 sentence summary)
- "issuing_authority": string
- "source_url": string

If a field cannot be determined, use "Not specified".
Return ONLY the raw JSON array, no markdown formatting or code blocks."""

        response = scout_llm.invoke(prompt)
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            opportunities = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            opportunities = []
            for r in raw_results[:6]:
                if isinstance(r, dict):
                    opportunities.append({
                        "tender_title": r.get("title", r.get("url", "Unknown")),
                        "summary": r.get("content", "No summary available.")[:200],
                        "issuing_authority": "Not specified",
                        "source_url": r.get("url", "#"),
                    })
        return {"opportunities": opportunities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tender scouting failed: {str(e)}")


@router.get("/api/scout-logs")
async def get_scout_logs() -> list[dict]:
    from app.core.database import supabase_client
    try:
        result = supabase_client.table("scout_logs").select("*").order("created_at", desc=True).limit(20).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scout logs: {str(e)}")


@router.post("/api/scout-trigger")
async def trigger_scout() -> dict:
    try:
        results = scout_and_alert()
        return {"status": "completed", "results_count": results.get("results_count", 0), "opportunities": results.get("opportunities", []),
                "categories_searched": results.get("categories_searched", []), "alert_sent": results.get("alert_sent", False)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual scout failed: {str(e)}")
