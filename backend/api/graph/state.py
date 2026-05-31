"""
state.py — Pydantic v2 & TypedDict State Schema Definitions

Defines the structural memory types for the LangGraph RFP processing workflow.
Three schemas enforce type safety across all graph nodes:
  1. RFPRequirement  — a single parsed requirement line from the uploaded RFP document
  2. SKURecommendation — a product match result for one requirement
  3. RFPState — the global graph state dict shared by all nodes
"""

from typing import Optional
from typing_extensions import TypedDict


# ─── Individual RFP requirement extracted from the raw document text ───
# Each line item in the RFP is parsed into this structure by the sales_discovery_node.
# Fields capture the electrical specification attributes needed for SKU matching.
class RFPRequirement(TypedDict):
    # Unique identifier for this line item within the RFP (e.g., "LI-001")
    line_item_id: str
    # The original unprocessed specification string from the RFP document
    raw_specification_string: str
    # Number of conductor cores specified (e.g., 3 for a 3-core cable)
    core_count: int
    # Conductor material type (e.g., "copper", "aluminium")
    conductor_material: str
    # Rated voltage in volts (e.g., 600.0, 1100.0) — drives MTO threshold logic
    voltage_rating: float
    # Insulation material type (e.g., "XLPE", "PVC", "EPR")
    insulation_type: str


# ─── SKU match result produced by the technical_matching_node ───
# One recommendation is generated per RFPRequirement after searching the product catalog.
# The is_custom_mto flag determines whether the item routes through MTO blueprint generation.
class SKURecommendation(TypedDict):
    # Internal product SKU identifier from the catalog (e.g., "SKU-CU-XLPE-3C-1100V")
    sku_id: str
    # Human-readable product name for the matched or nearest SKU
    product_name: str
    # Percentage indicating how closely the SKU matches the requirement (0.0–100.0)
    spec_match_percentage: float
    # True if the match is below threshold and requires a custom Make-to-Order modification
    is_custom_mto: bool
    # Explanation of specification gaps between the requirement and the nearest standard SKU
    gap_analysis_notes: str


# ─── Global graph state — single source of truth across all workflow nodes ───
# LangGraph passes this dict between every node. Each node reads from and writes to
# specific keys without mutating unrelated fields.
class RFPState(TypedDict):
    # The complete raw text content extracted from the uploaded RFP document (PDF/DOCX/TXT)
    raw_rfp_content: str
    # Document-level metadata extracted by sales_discovery_node (e.g., client name, RFP date)
    metadata: dict[str, str]
    # Ordered list of parsed technical requirements from the RFP
    extracted_requirements: list[RFPRequirement]
    # Ordered list of SKU recommendations aligned 1:1 with extracted_requirements
    matched_skus: list[SKURecommendation]
    # Markdown blueprints for each MTO item explaining the engineering modification delta
    mto_blueprints: list[str]
    # Per-SKU pricing breakdown with base and volatility-adjusted amounts
    pricing_breakdown: list[dict[str, float]]
    # Global multiplier applied to all base prices to account for commodity market volatility
    commodity_volatility_multiplier: float
    # Free-form notes injected by the human reviewer during the interrupt step (None if not yet reviewed)
    human_override_notes: Optional[str]
    # The final compiled markdown proposal document combining all analysis sections
    final_proposal_markdown: str
