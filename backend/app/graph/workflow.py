"""
workflow.py — Compiled LangGraph Multi-Agent State Graph

8-node StateGraph with conditional routing and human-in-the-loop interrupt.

Graph Topology:
  START → sales_discovery → technical_matching → compliance_router
    ├─ (any MTO) → generate_mto_blueprint → await_human_review → pricing_estimation
    └─ (all std) → pricing_estimation
  pricing_estimation → output_compiler → email_draft → END
"""

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver

from app.models.state import RFPState, RFPRequirement, SKURecommendation
from app.core.database import supabase_client
from app.core.config import get_settings

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)

MTO_MATCH_THRESHOLD = 75.0


def _extract_text(response) -> str:
    """Safely extract text from an LLM response, handling both str and list content."""
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


# ═══ NODE 1: Sales Discovery ═══
def sales_discovery_node(state: RFPState) -> dict:
    extraction_prompt = f"""You are an expert RFP analyst for an electrical cable manufacturing company.
Analyze the following RFP document and extract every individual cable/wire requirement as a structured JSON array.

For each requirement, extract these exact fields:
- "line_item_id": A sequential identifier like "LI-001", "LI-002", etc.
- "raw_specification_string": The original text describing this requirement verbatim.
- "core_count": Number of conductor cores as an integer (default to 1 if not specified).
- "conductor_material": The conductor material (e.g., "copper", "aluminium"). Default to "copper" if not specified.
- "voltage_rating": Rated voltage in volts as a float (e.g., 600.0, 1100.0). Extract from kV or V notations.
- "insulation_type": Insulation material (e.g., "XLPE", "PVC", "EPR"). Default to "PVC" if not specified.
- "cross_section_mm2": Conductor cross-sectional area in sq.mm as a float. Default to 1.5 if not specified.

Also extract document-level metadata as a separate JSON object with keys:
- "client_name": Name of the requesting organization (or "Unknown" if not found).
- "rfp_date": Date of the RFP document (or "Unknown" if not found).
- "project_name": Project or tender name (or "Unknown" if not found).

Return your response as a valid JSON object with exactly two keys:
  "metadata": {{ the metadata object }},
  "requirements": [ array of requirement objects ]

Do not include any text outside the JSON object. Do not use markdown code fences.

RFP DOCUMENT TEXT:
{state["raw_rfp_content"]}"""

    response = llm.invoke(extraction_prompt)
    raw_output = _extract_text(response).strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.split("\n", 1)[1]
    if raw_output.endswith("```"):
        raw_output = raw_output.rsplit("```", 1)[0]
    raw_output = raw_output.strip()

    parsed_data: dict = json.loads(raw_output)
    metadata = parsed_data.get("metadata", {"client_name": "Unknown", "rfp_date": "Unknown", "project_name": "Unknown"})

    extracted_requirements: list[RFPRequirement] = []
    for item in parsed_data.get("requirements", []):
        requirement: RFPRequirement = {
            "line_item_id": str(item.get("line_item_id", "LI-000")),
            "raw_specification_string": str(item.get("raw_specification_string", "")),
            "core_count": int(item.get("core_count", 1)),
            "conductor_material": str(item.get("conductor_material", "copper")),
            "voltage_rating": float(item.get("voltage_rating", 0.0)),
            "insulation_type": str(item.get("insulation_type", "PVC")),
            "cross_section_mm2": float(item.get("cross_section_mm2", 1.5)),
        }
        extracted_requirements.append(requirement)

    return {"metadata": metadata, "extracted_requirements": extracted_requirements}


# ═══ NODE 2: Technical Matching ═══
def _compute_match_score(requirement: dict, product: dict) -> float:
    score = 0.0
    req_material = requirement.get("conductor_material", "").lower().strip()
    prod_material = product.get("conductor_material", "").lower().strip()
    if req_material == prod_material:
        score += 20.0

    req_insulation = requirement.get("insulation_type", "").upper().strip()
    prod_insulation = product.get("insulation_type", "").upper().strip()
    if req_insulation == prod_insulation:
        score += 20.0
    elif {req_insulation, prod_insulation} == {"XLPE", "PVC"}:
        score += 8.0

    req_voltage = float(requirement.get("voltage_rating", 0))
    prod_voltage = float(product.get("voltage_rating", 0))
    if prod_voltage >= req_voltage and req_voltage > 0:
        score += 20.0
    elif req_voltage > 0:
        score += 20.0 * min(prod_voltage / req_voltage, 1.0)

    req_cores = int(requirement.get("core_count", 1))
    prod_cores = int(product.get("core_count", 1))
    if req_cores == prod_cores:
        score += 20.0
    elif abs(req_cores - prod_cores) == 1:
        score += 10.0

    req_size = float(requirement.get("cross_section_mm2", 0))
    prod_size = float(product.get("cross_section_mm2", 0))
    if req_size == prod_size and req_size > 0:
        score += 20.0
    elif req_size > 0 and prod_size > 0:
        score += 20.0 * (min(req_size, prod_size) / max(req_size, prod_size))

    return round(score, 1)


def _build_gap_notes(requirement: dict, product: dict, score: float) -> str:
    gaps = []
    rm = requirement.get("conductor_material", "").lower()
    pm = product.get("conductor_material", "").lower()
    if rm != pm:
        gaps.append(f"Material mismatch: requires {rm}, catalog has {pm}")
    ri = requirement.get("insulation_type", "").upper()
    pi = product.get("insulation_type", "").upper()
    if ri != pi:
        gaps.append(f"Insulation mismatch: requires {ri}, catalog has {pi}")
    rv = float(requirement.get("voltage_rating", 0))
    pv = float(product.get("voltage_rating", 0))
    if pv < rv:
        gaps.append(f"Voltage gap: requires {rv:.0f}V, catalog max is {pv:.0f}V")
    rc = int(requirement.get("core_count", 1))
    pc = int(product.get("core_count", 1))
    if rc != pc:
        gaps.append(f"Core count: requires {rc}C, catalog has {pc}C")
    rs = float(requirement.get("cross_section_mm2", 0))
    ps = float(product.get("cross_section_mm2", 0))
    if rs != ps and rs > 0:
        gaps.append(f"Cross-section gap: requires {rs} mm², catalog has {ps} mm²")
    if not gaps:
        return f"Direct catalog match ({score:.1f}% confidence). No modifications required."
    return "; ".join(gaps) + f". Overall match: {score:.1f}%."


def technical_matching_node(state: RFPState) -> dict:
    catalog_result = supabase_client.table("products").select("*").execute()
    catalog = catalog_result.data or []
    if not catalog:
        raise ValueError("Product catalog is empty. Run the migration/seed script first.")

    matched_skus: list[SKURecommendation] = []
    for requirement in state["extracted_requirements"]:
        best_score = 0.0
        best_product = None
        for product in catalog:
            score = _compute_match_score(requirement, product)
            if score > best_score:
                best_score = score
                best_product = product

        if best_product:
            req_voltage = float(requirement.get("voltage_rating", 0))
            prod_voltage = float(best_product.get("voltage_rating", 0))
            req_insulation = requirement.get("insulation_type", "").upper().strip()
            prod_insulation = best_product.get("insulation_type", "").upper().strip()
            req_size = float(requirement.get("cross_section_mm2", 0))
            prod_size = float(best_product.get("cross_section_mm2", 0))

            is_mto = (
                best_score < MTO_MATCH_THRESHOLD or
                prod_voltage < req_voltage or
                (req_insulation != prod_insulation and req_insulation in ("LSZH", "EPR")) or
                (req_size != prod_size and req_size > 0)
            )
            gap_notes = _build_gap_notes(requirement, best_product, best_score)
            recommendation: SKURecommendation = {
                "sku_id": best_product["sku_id"],
                "product_name": best_product["product_name"],
                "spec_match_percentage": best_score,
                "is_custom_mto": is_mto,
                "gap_analysis_notes": gap_notes,
            }
        else:
            recommendation: SKURecommendation = {
                "sku_id": "MTO-CUSTOM-BUILD",
                "product_name": f"Custom {requirement['core_count']}C {requirement['conductor_material'].title()} {requirement['insulation_type']} Cable",
                "spec_match_percentage": 0.0,
                "is_custom_mto": True,
                "gap_analysis_notes": "No matching products found. Full custom manufacturing required.",
            }
        matched_skus.append(recommendation)
    return {"matched_skus": matched_skus}


# ═══ ROUTER: Compliance Decision ═══
def compliance_router(state: RFPState) -> str:
    has_mto = any(sku["is_custom_mto"] for sku in state["matched_skus"])
    return "generate_mto_blueprint" if has_mto else "pricing_estimation"


# ═══ NODE 4: MTO Blueprint Generator ═══
def generate_mto_blueprint_node(state: RFPState) -> dict:
    mto_blueprints: list[str] = []
    mto_items = [
        (req, sku) for req, sku in zip(state["extracted_requirements"], state["matched_skus"])
        if sku["is_custom_mto"]
    ]
    for requirement, sku in mto_items:
        prompt = f"""You are a senior cable engineering specialist. Generate a detailed engineering
modification blueprint in markdown format for a custom Make-to-Order (MTO) cable product.

REQUIREMENT DETAILS:
- Line Item: {requirement["line_item_id"]}
- Specification: {requirement["raw_specification_string"]}
- Core Count: {requirement["core_count"]}
- Conductor Material: {requirement["conductor_material"]}
- Target Voltage Rating: {requirement["voltage_rating"]}V
- Insulation Type: {requirement["insulation_type"]}

NEAREST STANDARD SKU:
- SKU ID: {sku["sku_id"]}
- Match Percentage: {sku["spec_match_percentage"]}%
- Gap Analysis: {sku["gap_analysis_notes"]}

Generate a blueprint that includes:
1. **Modification Summary** — One-line description of the engineering change
2. **Technical Delta** — Specific changes to insulation thickness, conductor cross-section, shielding layers, etc.
3. **Manufacturing Process Changes** — Extrusion parameters, curing temperatures, testing protocols
4. **Quality Assurance Requirements** — Voltage withstand tests, partial discharge testing thresholds
5. **Estimated Lead Time Impact** — Additional days/weeks for custom manufacturing

Format as clean markdown with headers. Be specific with numerical values where applicable."""

        response = llm.invoke(prompt)
        full_blueprint = f"## MTO Blueprint — {requirement['line_item_id']} ({sku['sku_id']})\n\n{_extract_text(response).strip()}"
        mto_blueprints.append(full_blueprint)
    return {"mto_blueprints": mto_blueprints}


# ═══ NODE 5: Human-in-the-Loop Review Gate ═══
def await_human_review_node(state: RFPState) -> dict:
    review_payload = {
        "alert": "MTO Blueprint Review Required",
        "message": "One or more items require custom Make-to-Order manufacturing.",
        "blueprints": state["mto_blueprints"],
        "matched_skus": [
            {
                "sku_id": s["sku_id"], "product_name": s["product_name"],
                "spec_match_percentage": s["spec_match_percentage"],
                "is_custom_mto": s["is_custom_mto"], "gap_analysis_notes": s["gap_analysis_notes"],
            }
            for s in state["matched_skus"]
        ],
        "current_multiplier": state.get("commodity_volatility_multiplier", 1.0),
    }
    human_input = interrupt(review_payload)
    override_notes = human_input.get("human_override_notes", "No additional notes provided.")
    adjusted_multiplier = float(human_input.get("commodity_volatility_multiplier", 1.0))
    approved_by = human_input.get("approved_by", "")
    result = {"human_override_notes": override_notes, "commodity_volatility_multiplier": adjusted_multiplier}
    if approved_by:
        result["approved_by"] = approved_by
    return result


# ═══ NODE 6: Pricing Estimation ═══
def pricing_estimation_node(state: RFPState) -> dict:
    multiplier = state.get("commodity_volatility_multiplier", 1.0)
    pricing_breakdown: list[dict[str, float]] = []
    for requirement, sku in zip(state["extracted_requirements"], state["matched_skus"]):
        core_factor = requirement["core_count"] * 12.50
        voltage_factor = requirement["voltage_rating"] * 0.05
        material_premium = 1.35 if requirement["conductor_material"].lower() == "copper" else 1.0
        mto_surcharge = 1.25 if sku["is_custom_mto"] else 1.0
        base = round((core_factor + voltage_factor) * material_premium * mto_surcharge, 2)
        adjusted = round(base * multiplier, 2)
        pricing_breakdown.append({
            "sku_id": sku["sku_id"], "core_count": float(requirement["core_count"]),
            "voltage_rating": requirement["voltage_rating"],
            "base_price_per_meter": base, "volatility_multiplier": multiplier,
            "adjusted_price_per_meter": adjusted,
        })
    return {"pricing_breakdown": pricing_breakdown}


# ═══ NODE 7: Output Compiler ═══
def output_compiler_node(state: RFPState) -> dict:
    metadata = state.get("metadata", {})
    requirements = state.get("extracted_requirements", [])
    skus = state.get("matched_skus", [])
    blueprints = state.get("mto_blueprints", [])
    pricing = state.get("pricing_breakdown", [])
    override_notes = state.get("human_override_notes")
    multiplier = state.get("commodity_volatility_multiplier", 1.0)

    s: list[str] = []
    s.append("# RFP Technical Proposal\n")
    s.append(f"**Client:** {metadata.get('client_name', 'N/A')}")
    s.append(f"**Project:** {metadata.get('project_name', 'N/A')}")
    s.append(f"**RFP Date:** {metadata.get('rfp_date', 'N/A')}")
    s.append(f"**Commodity Volatility Multiplier:** {multiplier}x")
    s.append("")
    s.append("---\n")
    s.append("## Technical Requirements Matrix\n")
    s.append("| Line Item | Cores | Material | Voltage (V) | Insulation | Specification |")
    s.append("|-----------|-------|----------|-------------|------------|---------------|")
    for req in requirements:
        spec = req['raw_specification_string'][:60] + ('...' if len(req['raw_specification_string']) > 60 else '')
        s.append(f"| {req['line_item_id']} | {req['core_count']} | {req['conductor_material']} | {req['voltage_rating']:.0f} | {req['insulation_type']} | {spec} |")
    s.append("")
    s.append("---\n")
    s.append("## SKU Matching Results\n")
    s.append("| SKU ID | Product Name | Match % | Custom MTO | Gap Analysis |")
    s.append("|--------|-------------|---------|------------|--------------|")
    for sku in skus:
        mto = "🔧 Yes" if sku["is_custom_mto"] else "✅ No"
        gap = sku['gap_analysis_notes'][:50] + ('...' if len(sku['gap_analysis_notes']) > 50 else '')
        s.append(f"| {sku['sku_id']} | {sku['product_name']} | {sku['spec_match_percentage']:.1f}% | {mto} | {gap} |")
    s.append("")
    if blueprints:
        s.append("---\n")
        s.append("## Make-to-Order (MTO) Engineering Blueprints\n")
        for bp in blueprints:
            s.append(bp)
            s.append("")
    s.append("---\n")
    s.append("## Pricing Breakdown\n")
    s.append("| SKU ID | Cores | Voltage (V) | Base Price/m | Multiplier | Adjusted Price/m |")
    s.append("|--------|-------|-------------|-------------|------------|-----------------|")
    total_base = total_adj = 0.0
    for item in pricing:
        s.append(f"| {item['sku_id']} | {item['core_count']:.0f} | {item['voltage_rating']:.0f} | ${item['base_price_per_meter']:.2f} | {item['volatility_multiplier']:.2f}x | ${item['adjusted_price_per_meter']:.2f} |")
        total_base += item["base_price_per_meter"]
        total_adj += item["adjusted_price_per_meter"]
    s.append(f"\n**Total Base Price (all items):** ${total_base:.2f}/m")
    s.append(f"**Total Adjusted Price (all items):** ${total_adj:.2f}/m")
    s.append("")
    if override_notes:
        s.append("---\n")
        s.append("## Human Review Notes\n")
        s.append(f"> {override_notes}")
        s.append("")
    approved_by = state.get("approved_by")
    if approved_by:
        s.append("---\n")
        s.append("## Approval\n")
        s.append(f"**Approved By:** {approved_by}")
        s.append("")
    s.append("---\n")
    s.append("*This proposal was generated by the FMCG RFP Processing Pipeline.*")
    return {"final_proposal_markdown": "\n".join(s)}


# ═══ NODE 8: Email Draft Generator ═══
def email_draft_node(state: RFPState) -> dict:
    metadata = state.get("metadata", {})
    client_name = metadata.get("client_name", "Valued Client")
    project_name = metadata.get("project_name", "Infrastructure Project")
    matched_skus = state.get("matched_skus", [])
    pricing = state.get("pricing_breakdown", [])
    total_items = len(matched_skus)
    mto_items = sum(1 for s in matched_skus if s.get("is_custom_mto"))
    std_items = total_items - mto_items
    total_value = sum(p.get("adjusted_price_per_meter", p.get("base_price_per_meter", 0)) for p in pricing)

    prompt = f"""You are a senior sales executive at FMCG Industrial Solutions, a leading electrical cable manufacturer.
Draft a professional, persuasive bid submission email for the following RFP response.

CLIENT: {client_name}
PROJECT: {project_name}
ITEMS QUOTED: {total_items} line items ({std_items} standard catalog matches, {mto_items} custom MTO)
ESTIMATED VALUE: INR {total_value:,.2f}
COMPLIANCE: IEC 60502 / IS 7098 certified
DELIVERY: Standard items 3-14 days, MTO items 14-25 days

The email should:
1. Open with a professional greeting referencing the project name
2. Highlight competitive advantages (direct manufacturer pricing, certified products, fast delivery)
3. Summarize the bid
4. Mention ability to handle both standard and custom Make-to-Order requirements
5. Close with a call to action for a technical review meeting
6. Include a professional signature block for "FMCG Industrial Solutions"

Write in plain text format. Keep it concise (250-350 words)."""

    response = llm.invoke(prompt)
    return {"outreach_email_draft": _extract_text(response).strip()}


# ═══ GRAPH ASSEMBLY ═══
graph_builder = StateGraph(RFPState)
graph_builder.add_node("sales_discovery", sales_discovery_node)
graph_builder.add_node("technical_matching", technical_matching_node)
graph_builder.add_node("generate_mto_blueprint", generate_mto_blueprint_node)
graph_builder.add_node("await_human_review", await_human_review_node)
graph_builder.add_node("pricing_estimation", pricing_estimation_node)
graph_builder.add_node("output_compiler", output_compiler_node)
graph_builder.add_node("email_draft", email_draft_node)

graph_builder.add_edge(START, "sales_discovery")
graph_builder.add_edge("sales_discovery", "technical_matching")
graph_builder.add_conditional_edges(
    "technical_matching", compliance_router,
    {"generate_mto_blueprint": "generate_mto_blueprint", "pricing_estimation": "pricing_estimation"},
)
graph_builder.add_edge("generate_mto_blueprint", "await_human_review")
graph_builder.add_edge("await_human_review", "pricing_estimation")
graph_builder.add_edge("pricing_estimation", "output_compiler")
graph_builder.add_edge("output_compiler", "email_draft")
graph_builder.add_edge("email_draft", END)

# ── Compile with PostgresSaver checkpointer (Fallback to MemorySaver if offline) ──
import psycopg
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.memory import MemorySaver

_db_url = get_settings().DATABASE_URL

try:
    if not _db_url:
        raise ValueError("DATABASE_URL is not set")
    _setup_conn = psycopg.connect(_db_url, autocommit=True)
    _setup_checkpointer = PostgresSaver(_setup_conn)
    _setup_checkpointer.setup()
    _setup_conn.close()

    _connection_pool = ConnectionPool(
        conninfo=_db_url,
        max_size=5,
        kwargs={"autocommit": True},
    )
    checkpointer = PostgresSaver(_connection_pool)
    rfp_workflow = graph_builder.compile(checkpointer=checkpointer)
except Exception as e:
    print(f"\n[WARNING] Database connection failed ({e}). Falling back to MemorySaver in-memory checkpointer.\n")
    rfp_workflow = graph_builder.compile(checkpointer=MemorySaver())


