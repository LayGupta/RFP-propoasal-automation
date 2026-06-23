"""history router — /api/history and /api/analytics endpoints"""

from fastapi import APIRouter, HTTPException, Depends

from app.core.security import UserClaims
from app.core.database import supabase_client
from app.routers.auth import get_current_user

router = APIRouter(tags=["history"])


@router.get("/api/history")
async def get_proposal_history(user: UserClaims = Depends(get_current_user)) -> list[dict]:
    try:
        result = (
            supabase_client.table("proposals")
            .select("id, thread_id, project_name, final_markdown, created_at")
            .eq("user_id", user.user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.get("/api/analytics")
async def get_analytics(user: UserClaims = Depends(get_current_user)) -> dict:
    try:
        proposals = supabase_client.table("proposals").select("id, created_at, thread_id, project_name").eq("user_id", user.user_id).execute()
        total_proposals = len(proposals.data or [])

        products = supabase_client.table("products").select("sku_id, product_name, conductor_material, category, base_price_per_meter, stock_quantity").execute()
        product_list = products.data or []
        total_products = len(product_list)
        total_inventory_value = sum(p["base_price_per_meter"] * p["stock_quantity"] for p in product_list)

        copper_count = sum(1 for p in product_list if p["conductor_material"] == "copper")
        aluminium_count = total_products - copper_count

        proposals_by_day: dict[str, int] = {}
        for p in (proposals.data or []):
            day = p["created_at"][:10] if p.get("created_at") else "unknown"
            proposals_by_day[day] = proposals_by_day.get(day, 0) + 1

        proposals_timeline = [{"date": k, "count": v} for k, v in sorted(proposals_by_day.items())[-30:]]

        scout_logs = supabase_client.table("scout_logs").select("id, query, results_count, alert_sent, created_at").order("created_at", desc=True).limit(10).execute()

        return {
            "total_proposals": total_proposals,
            "total_products": total_products,
            "total_inventory_value": round(total_inventory_value, 2),
            "copper_products": copper_count,
            "aluminium_products": aluminium_count,
            "proposals_timeline": proposals_timeline,
            "scout_logs": scout_logs.data or [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")
