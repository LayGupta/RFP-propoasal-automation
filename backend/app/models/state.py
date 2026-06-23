"""
state.py — LangGraph State Schema Definitions

Three TypedDict schemas enforce type safety across all graph nodes:
  1. RFPRequirement  — a single parsed requirement line from the uploaded RFP document
  2. SKURecommendation — a product match result for one requirement
  3. RFPState — the global graph state dict shared by all nodes
"""

from typing import Optional
from typing_extensions import TypedDict


class RFPRequirement(TypedDict):
    line_item_id: str
    raw_specification_string: str
    core_count: int
    conductor_material: str
    voltage_rating: float
    insulation_type: str
    cross_section_mm2: float


class SKURecommendation(TypedDict):
    sku_id: str
    product_name: str
    spec_match_percentage: float
    is_custom_mto: bool
    gap_analysis_notes: str


class RFPState(TypedDict):
    raw_rfp_content: str
    metadata: dict[str, str]
    extracted_requirements: list[RFPRequirement]
    matched_skus: list[SKURecommendation]
    mto_blueprints: list[str]
    pricing_breakdown: list[dict[str, float]]
    commodity_volatility_multiplier: float
    human_override_notes: Optional[str]
    final_proposal_markdown: str
    approved_by: Optional[str]
    user_id: Optional[str]
    outreach_email_draft: Optional[str]
