"""
workflow.py — Compiled LangGraph Multi-Agent State Graph

Assembles a 7-node StateGraph using RFPState as the shared memory schema.
Nodes execute sequentially with one conditional branch (compliance_router)
and one human-in-the-loop interrupt (await_human_review_node).

Graph Topology:
  START → sales_discovery → technical_matching → compliance_router
    ├─ (any MTO) → generate_mto_blueprint → await_human_review → pricing_estimation
    └─ (all std) → pricing_estimation
  pricing_estimation → output_compiler → END

Compiled with PostgresSaver checkpointer for persistent state across serverless invocations.
"""

import json
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver

from api.graph.state import RFPState, RFPRequirement, SKURecommendation
from api.database.client import connection_pool, supabase_client


# ─── Shared LLM instance ───
# ChatGroq reads GROQ_API_KEY from environment automatically via langchain convention.
# temperature=0 ensures deterministic, reproducible outputs across all agent nodes.
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 1: Sales Discovery Agent
# Transforms raw RFP document text into structured requirement dictionaries.
# This is the entry point that converts unstructured natural language into
# machine-parseable specifications for downstream matching.
# ═══════════════════════════════════════════════════════════════════════════════
def sales_discovery_node(state: RFPState) -> dict:
    """Parse raw RFP text into structured RFPRequirement dicts using LLM extraction."""

    # Construct a precise prompt that forces JSON array output matching our TypedDict schema
    extraction_prompt = f"""You are an expert RFP analyst for an electrical cable manufacturing company.
Analyze the following RFP document and extract every individual cable/wire requirement as a structured JSON array.

For each requirement, extract these exact fields:
- "line_item_id": A sequential identifier like "LI-001", "LI-002", etc.
- "raw_specification_string": The original text describing this requirement verbatim.
- "core_count": Number of conductor cores as an integer (default to 1 if not specified).
- "conductor_material": The conductor material (e.g., "copper", "aluminium"). Default to "copper" if not specified.
- "voltage_rating": Rated voltage in volts as a float (e.g., 600.0, 1100.0). Extract from kV or V notations.
- "insulation_type": Insulation material (e.g., "XLPE", "PVC", "EPR"). Default to "PVC" if not specified.

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

    # Invoke the LLM to perform structured extraction from natural language
    response = llm.invoke(extraction_prompt)
    raw_output = response.content.strip()

    # Strip markdown code fences if the LLM wraps output in them despite instructions
    if raw_output.startswith("```"):
        raw_output = raw_output.split("\n", 1)[1]
    if raw_output.endswith("```"):
        raw_output = raw_output.rsplit("```", 1)[0]
    raw_output = raw_output.strip()

    # Parse the JSON response into Python structures
    parsed_data: dict = json.loads(raw_output)

    # Extract metadata with fallback defaults for robustness
    metadata: dict[str, str] = parsed_data.get("metadata", {
        "client_name": "Unknown",
        "rfp_date": "Unknown",
        "project_name": "Unknown",
    })

    # Build typed requirement list from the parsed JSON array
    extracted_requirements: list[RFPRequirement] = []
    for item in parsed_data.get("requirements", []):
        requirement: RFPRequirement = {
            "line_item_id": str(item.get("line_item_id", "LI-000")),
            "raw_specification_string": str(item.get("raw_specification_string", "")),
            "core_count": int(item.get("core_count", 1)),
            "conductor_material": str(item.get("conductor_material", "copper")),
            "voltage_rating": float(item.get("voltage_rating", 0.0)),
            "insulation_type": str(item.get("insulation_type", "PVC")),
        }
        extracted_requirements.append(requirement)

    # Return state updates — LangGraph merges these into the global RFPState dict
    return {
        "metadata": metadata,
        "extracted_requirements": extracted_requirements,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 2: Technical Matching Agent
# Queries the `products` table in Supabase and computes a weighted similarity
# score for each RFP requirement against every catalog product.
# Scoring weights: conductor material (25%), insulation type (25%),
# voltage rating (25%), core count (25%).
# Products scoring ≥75% are standard matches; below 75% are flagged as MTO.
# ═══════════════════════════════════════════════════════════════════════════════

# MTO threshold — products below this match score require custom manufacturing
MTO_MATCH_THRESHOLD = 75.0


def _compute_match_score(requirement: dict, product: dict) -> float:
    """Compute a weighted similarity score (0-100) between a requirement and a catalog product.

    Scoring breakdown:
      - Conductor material: 25% (exact match = 100%, mismatch = 0%)
      - Insulation type:    25% (exact = 100%, XLPE↔PVC partial = 40%, else 0%)
      - Voltage rating:     25% (product ≥ requirement = 100%, below = proportional)
      - Core count:         25% (exact = 100%, ±1 = 50%, else 0%)
    """
    score = 0.0

    # Conductor material (25%)
    req_material = requirement.get("conductor_material", "").lower().strip()
    prod_material = product.get("conductor_material", "").lower().strip()
    if req_material == prod_material:
        score += 25.0

    # Insulation type (25%)
    req_insulation = requirement.get("insulation_type", "").upper().strip()
    prod_insulation = product.get("insulation_type", "").upper().strip()
    if req_insulation == prod_insulation:
        score += 25.0
    elif {req_insulation, prod_insulation} == {"XLPE", "PVC"}:
        # Partial match — same family but different performance tier
        score += 10.0

    # Voltage rating (25%)
    req_voltage = float(requirement.get("voltage_rating", 0))
    prod_voltage = float(product.get("voltage_rating", 0))
    if prod_voltage >= req_voltage and req_voltage > 0:
        score += 25.0
    elif req_voltage > 0:
        # Proportional score if product voltage is below requirement
        ratio = prod_voltage / req_voltage
        score += 25.0 * min(ratio, 1.0)

    # Core count (25%)
    req_cores = int(requirement.get("core_count", 1))
    prod_cores = int(product.get("core_count", 1))
    if req_cores == prod_cores:
        score += 25.0
    elif abs(req_cores - prod_cores) == 1:
        score += 12.5

    return round(score, 1)


def _build_gap_notes(requirement: dict, product: dict, score: float) -> str:
    """Generate human-readable gap analysis explaining the match delta."""
    gaps = []

    req_material = requirement.get("conductor_material", "").lower()
    prod_material = product.get("conductor_material", "").lower()
    if req_material != prod_material:
        gaps.append(f"Material mismatch: requires {req_material}, catalog has {prod_material}")

    req_insulation = requirement.get("insulation_type", "").upper()
    prod_insulation = product.get("insulation_type", "").upper()
    if req_insulation != prod_insulation:
        gaps.append(f"Insulation mismatch: requires {req_insulation}, catalog has {prod_insulation}")

    req_voltage = float(requirement.get("voltage_rating", 0))
    prod_voltage = float(product.get("voltage_rating", 0))
    if prod_voltage < req_voltage:
        gaps.append(f"Voltage gap: requires {req_voltage:.0f}V, catalog max is {prod_voltage:.0f}V (delta: {req_voltage - prod_voltage:.0f}V)")

    req_cores = int(requirement.get("core_count", 1))
    prod_cores = int(product.get("core_count", 1))
    if req_cores != prod_cores:
        gaps.append(f"Core count: requires {req_cores}C, catalog has {prod_cores}C")

    if not gaps:
        return f"Direct catalog match ({score:.1f}% confidence). No modifications required."

    return "; ".join(gaps) + f". Overall match: {score:.1f}%."


def technical_matching_node(state: RFPState) -> dict:
    """Match each requirement against the real product catalog using weighted similarity scoring."""

    # Step 1: Fetch the full product catalog from Supabase
    catalog_result = supabase_client.table("products").select("*").execute()
    catalog = catalog_result.data or []

    if not catalog:
        # Fallback if catalog is empty — should not happen after seeding
        raise ValueError("Product catalog is empty. Run the migration/seed script first.")

    matched_skus: list[SKURecommendation] = []

    for requirement in state["extracted_requirements"]:
        best_score = 0.0
        best_product = None

        # Step 2: Score every catalog product against this requirement
        for product in catalog:
            score = _compute_match_score(requirement, product)
            if score > best_score:
                best_score = score
                best_product = product

        # Step 3: Build the SKU recommendation from the best match
        if best_product:
            is_mto = best_score < MTO_MATCH_THRESHOLD
            gap_notes = _build_gap_notes(requirement, best_product, best_score)

            recommendation: SKURecommendation = {
                "sku_id": best_product["sku_id"],
                "product_name": best_product["product_name"],
                "spec_match_percentage": best_score,
                "is_custom_mto": is_mto,
                "gap_analysis_notes": gap_notes,
            }
        else:
            # No products in catalog at all — flag as full MTO
            recommendation: SKURecommendation = {
                "sku_id": "MTO-CUSTOM-BUILD",
                "product_name": f"Custom {requirement['core_count']}C {requirement['conductor_material'].title()} {requirement['insulation_type']} Cable",
                "spec_match_percentage": 0.0,
                "is_custom_mto": True,
                "gap_analysis_notes": "No matching products found in catalog. Full custom manufacturing required.",
            }

        matched_skus.append(recommendation)

    # Return the complete list of SKU recommendations aligned with extracted_requirements
    return {"matched_skus": matched_skus}


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER: Compliance Decision Function
# Reads matched_skus from state and routes execution based on MTO presence.
# This is NOT a node — it's a pure function used by add_conditional_edges().
# Returns a string key that maps to the next node in the graph topology.
# ═══════════════════════════════════════════════════════════════════════════════
def compliance_router(state: RFPState) -> str:
    """Route to MTO blueprint generation if any SKU requires custom manufacturing."""

    # Check if any matched SKU has been flagged as requiring custom Make-to-Order
    has_mto_items = any(
        sku["is_custom_mto"] for sku in state["matched_skus"]
    )

    if has_mto_items:
        # At least one item needs custom manufacturing — route to blueprint generation
        return "generate_mto_blueprint"
    else:
        # All items are standard catalog matches — skip directly to pricing
        return "pricing_estimation"


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 4: MTO Blueprint Generator
# Uses ChatGroq to produce structured markdown engineering modification profiles
# for each SKU flagged as is_custom_mto=True. Describes the exact manufacturing
# delta (e.g., insulation thickening, conductor upsizing) needed.
# ═══════════════════════════════════════════════════════════════════════════════
def generate_mto_blueprint_node(state: RFPState) -> dict:
    """Generate engineering modification blueprints for all custom MTO items."""

    mto_blueprints: list[str] = []

    # Filter to only the SKUs that require custom manufacturing modifications
    mto_items = [
        (req, sku)
        for req, sku in zip(state["extracted_requirements"], state["matched_skus"])
        if sku["is_custom_mto"]
    ]

    for requirement, sku in mto_items:
        # Construct a domain-specific prompt for engineering blueprint generation
        blueprint_prompt = f"""You are a senior cable engineering specialist. Generate a detailed engineering 
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

Format as clean markdown with headers. Be specific with numerical values where applicable.
For example, if the voltage is 1100V, specify thickening the XLPE insulation extrusion layer 
from the standard 1.0mm to 1.5mm to handle the increased dielectric stress."""

        # Invoke LLM to generate the engineering modification profile
        response = llm.invoke(blueprint_prompt)
        blueprint_markdown = response.content.strip()

        # Prepend a header with the line item reference for traceability
        full_blueprint = f"## MTO Blueprint — {requirement['line_item_id']} ({sku['sku_id']})\n\n{blueprint_markdown}"
        mto_blueprints.append(full_blueprint)

    # Return all generated blueprints to be stored in state for human review
    return {"mto_blueprints": mto_blueprints}


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 5: Human-in-the-Loop Review Gate
# IMPLEMENTS LANGGRAPH INTERRUPT PRIMITIVE. Pauses graph execution and surfaces
# the MTO blueprint data to the calling API endpoint. When resumed externally
# via Command(resume=...), captures the human reviewer's override notes and
# adjusted commodity volatility multiplier.
# ═══════════════════════════════════════════════════════════════════════════════
def await_human_review_node(state: RFPState) -> dict:
    """Pause execution for human review of MTO blueprints and commodity pricing adjustment."""

    # Construct the alert payload that will be surfaced to the frontend via the API
    review_payload = {
        "alert": "MTO Blueprint Review Required",
        "message": "One or more items require custom Make-to-Order manufacturing. Please review the blueprints below and adjust the commodity volatility multiplier if needed.",
        "blueprints": state["mto_blueprints"],
        "matched_skus": [
            {
                "sku_id": sku["sku_id"],
                "product_name": sku["product_name"],
                "spec_match_percentage": sku["spec_match_percentage"],
                "is_custom_mto": sku["is_custom_mto"],
                "gap_analysis_notes": sku["gap_analysis_notes"],
            }
            for sku in state["matched_skus"]
        ],
        "current_multiplier": state.get("commodity_volatility_multiplier", 1.0),
    }

    # INTERRUPT: Pause graph execution and persist state to PostgreSQL checkpointer.
    # The interrupt() call returns the value passed via Command(resume=...) when execution resumes.
    human_input = interrupt(review_payload)

    # After resume: human_input contains the reviewer's adjustments
    # Expected structure: {"human_override_notes": str, "commodity_volatility_multiplier": float, "approved_by": str}
    override_notes: str = human_input.get("human_override_notes", "No additional notes provided.")
    adjusted_multiplier: float = float(human_input.get("commodity_volatility_multiplier", 1.0))
    approved_by: str = human_input.get("approved_by", "")

    # Return the human reviewer's inputs to update the global state
    result = {
        "human_override_notes": override_notes,
        "commodity_volatility_multiplier": adjusted_multiplier,
    }
    if approved_by:
        result["approved_by"] = approved_by
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 6: Pricing Estimation Engine
# Calculates base prices for each matched SKU and applies the commodity
# volatility multiplier (which may have been adjusted by the human reviewer).
# Base prices are simulated using a deterministic formula based on cable specs.
# ═══════════════════════════════════════════════════════════════════════════════
def pricing_estimation_node(state: RFPState) -> dict:
    """Calculate volatility-adjusted pricing for all matched SKUs."""

    # Read the current volatility multiplier (1.0 if no human adjustment was made)
    multiplier: float = state.get("commodity_volatility_multiplier", 1.0)

    pricing_breakdown: list[dict[str, float]] = []

    for requirement, sku in zip(state["extracted_requirements"], state["matched_skus"]):
        # Simulate base price using a deterministic formula based on cable specifications
        # Base price factors: core count, voltage tier, and conductor material premium
        core_factor = requirement["core_count"] * 12.50
        voltage_factor = requirement["voltage_rating"] * 0.05
        material_premium = 1.35 if requirement["conductor_material"].lower() == "copper" else 1.0
        mto_surcharge = 1.25 if sku["is_custom_mto"] else 1.0

        # Calculate the base price per unit length (per meter) before volatility adjustment
        base_price_per_meter = round((core_factor + voltage_factor) * material_premium * mto_surcharge, 2)

        # Apply the commodity volatility multiplier to get the final adjusted price
        adjusted_price_per_meter = round(base_price_per_meter * multiplier, 2)

        pricing_breakdown.append({
            "sku_id": sku["sku_id"],
            "core_count": float(requirement["core_count"]),
            "voltage_rating": requirement["voltage_rating"],
            "base_price_per_meter": base_price_per_meter,
            "volatility_multiplier": multiplier,
            "adjusted_price_per_meter": adjusted_price_per_meter,
        })

    # Return the complete pricing breakdown for all SKUs
    return {"pricing_breakdown": pricing_breakdown}


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 7: Output Compiler
# Concatenates all analysis sections into a single structured markdown proposal.
# This is the final deliverable document that combines technical specs, matching
# results, MTO blueprints, pricing, and human override notes.
# ═══════════════════════════════════════════════════════════════════════════════
def output_compiler_node(state: RFPState) -> dict:
    """Compile all workflow outputs into a final structured markdown proposal document."""

    metadata = state.get("metadata", {})
    requirements = state.get("extracted_requirements", [])
    skus = state.get("matched_skus", [])
    blueprints = state.get("mto_blueprints", [])
    pricing = state.get("pricing_breakdown", [])
    override_notes = state.get("human_override_notes")
    multiplier = state.get("commodity_volatility_multiplier", 1.0)

    # Build the markdown document section by section
    sections: list[str] = []

    # ── Header section with document metadata ──
    sections.append("# RFP Technical Proposal\n")
    sections.append(f"**Client:** {metadata.get('client_name', 'N/A')}")
    sections.append(f"**Project:** {metadata.get('project_name', 'N/A')}")
    sections.append(f"**RFP Date:** {metadata.get('rfp_date', 'N/A')}")
    sections.append(f"**Commodity Volatility Multiplier:** {multiplier}x")
    sections.append("")

    # ── Technical Requirements Matrix ──
    sections.append("---\n")
    sections.append("## Technical Requirements Matrix\n")
    sections.append("| Line Item | Cores | Material | Voltage (V) | Insulation | Specification |")
    sections.append("|-----------|-------|----------|-------------|------------|---------------|")
    for req in requirements:
        sections.append(
            f"| {req['line_item_id']} | {req['core_count']} | {req['conductor_material']} "
            f"| {req['voltage_rating']:.0f} | {req['insulation_type']} "
            f"| {req['raw_specification_string'][:60]}{'...' if len(req['raw_specification_string']) > 60 else ''} |"
        )
    sections.append("")

    # ── SKU Matching Results ──
    sections.append("---\n")
    sections.append("## SKU Matching Results\n")
    sections.append("| SKU ID | Product Name | Match % | Custom MTO | Gap Analysis |")
    sections.append("|--------|-------------|---------|------------|--------------|")
    for sku in skus:
        mto_badge = "🔧 Yes" if sku["is_custom_mto"] else "✅ No"
        sections.append(
            f"| {sku['sku_id']} | {sku['product_name']} "
            f"| {sku['spec_match_percentage']:.1f}% | {mto_badge} "
            f"| {sku['gap_analysis_notes'][:50]}{'...' if len(sku['gap_analysis_notes']) > 50 else ''} |"
        )
    sections.append("")

    # ── MTO Blueprints section (only if any exist) ──
    if blueprints:
        sections.append("---\n")
        sections.append("## Make-to-Order (MTO) Engineering Blueprints\n")
        for blueprint in blueprints:
            sections.append(blueprint)
            sections.append("")

    # ── Pricing Breakdown ──
    sections.append("---\n")
    sections.append("## Pricing Breakdown\n")
    sections.append("| SKU ID | Cores | Voltage (V) | Base Price/m | Multiplier | Adjusted Price/m |")
    sections.append("|--------|-------|-------------|-------------|------------|-----------------|")
    total_base = 0.0
    total_adjusted = 0.0
    for item in pricing:
        sections.append(
            f"| {item['sku_id']} | {item['core_count']:.0f} | {item['voltage_rating']:.0f} "
            f"| ${item['base_price_per_meter']:.2f} | {item['volatility_multiplier']:.2f}x "
            f"| ${item['adjusted_price_per_meter']:.2f} |"
        )
        total_base += item["base_price_per_meter"]
        total_adjusted += item["adjusted_price_per_meter"]
    sections.append(f"\n**Total Base Price (all items):** ${total_base:.2f}/m")
    sections.append(f"**Total Adjusted Price (all items):** ${total_adjusted:.2f}/m")
    sections.append("")

    # ── Human Override Notes (only if reviewer provided input) ──
    if override_notes:
        sections.append("---\n")
        sections.append("## Human Review Notes\n")
        sections.append(f"> {override_notes}")
        sections.append("")

    # ── Approval Stamp (only if an authenticated user approved the MTO review) ──
    approved_by = state.get("approved_by")
    if approved_by:
        sections.append("---\n")
        sections.append("## Approval\n")
        sections.append(f"**Approved By:** {approved_by}")
        sections.append("")

    # ── Footer ──
    sections.append("---\n")
    sections.append("*This proposal was generated by the FMCG RFP Processing Pipeline.*")

    # Join all sections into the final markdown string
    final_markdown = "\n".join(sections)

    return {"final_proposal_markdown": final_markdown}


# ═══════════════════════════════════════════════════════════════════════════════
# NODE 8: Outreach Email Draft Generator
# Uses ChatGroq to draft a professional bid submission email summarizing
# the proposal's competitive advantages: pricing, compliance, delivery.
# ═══════════════════════════════════════════════════════════════════════════════
def email_draft_node(state: RFPState) -> dict:
    """Generate a professional outreach email draft for client submission."""

    metadata = state.get("metadata", {})
    client_name = metadata.get("client_name", "Valued Client")
    project_name = metadata.get("project_name", "Infrastructure Project")
    matched_skus = state.get("matched_skus", [])
    pricing = state.get("pricing_breakdown", [])

    # Count standard vs MTO items
    total_items = len(matched_skus)
    mto_items = sum(1 for s in matched_skus if s.get("is_custom_mto"))
    std_items = total_items - mto_items

    # Calculate total value
    total_value = sum(p.get("adjusted_price", p.get("base_price", 0)) for p in pricing)

    email_prompt = f"""You are a senior sales executive at FMCG Industrial Solutions, a leading electrical cable manufacturer.
Draft a professional, persuasive bid submission email for the following RFP response.

CLIENT: {client_name}
PROJECT: {project_name}
ITEMS QUOTED: {total_items} line items ({std_items} standard catalog matches, {mto_items} custom MTO)
ESTIMATED VALUE: INR {total_value:,.2f}
COMPLIANCE: IEC 60502 / IS 7098 certified
DELIVERY: Standard items 3-14 days, MTO items 14-25 days

The email should:
1. Open with a professional greeting referencing the project name
2. Highlight our competitive advantages (direct manufacturer pricing, certified products, fast delivery)
3. Summarize the bid (number of items, compliance standards, estimated value)
4. Mention our ability to handle both standard and custom Make-to-Order requirements
5. Close with a call to action for a technical review meeting
6. Include a professional signature block for "FMCG Industrial Solutions"

Write the email in plain text format suitable for business communication. Keep it concise (250-350 words)."""

    response = llm.invoke(email_prompt)
    email_draft = response.content.strip()

    return {"outreach_email_draft": email_draft}


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY — Wire all nodes and edges into a compiled StateGraph
# ═══════════════════════════════════════════════════════════════════════════════

# Initialize the state graph builder with our global state schema
graph_builder = StateGraph(RFPState)

# Register all 8 nodes (including human review interrupt and email draft)
graph_builder.add_node("sales_discovery", sales_discovery_node)
graph_builder.add_node("technical_matching", technical_matching_node)
graph_builder.add_node("generate_mto_blueprint", generate_mto_blueprint_node)
graph_builder.add_node("await_human_review", await_human_review_node)
graph_builder.add_node("pricing_estimation", pricing_estimation_node)
graph_builder.add_node("output_compiler", output_compiler_node)
graph_builder.add_node("email_draft", email_draft_node)

# Wire the linear edge from START to the first processing node
graph_builder.add_edge(START, "sales_discovery")

# Wire the linear edge from sales discovery to technical matching
graph_builder.add_edge("sales_discovery", "technical_matching")

# Add the conditional compliance router after technical matching
# Routes to either MTO blueprint generation or directly to pricing
graph_builder.add_conditional_edges(
    "technical_matching",
    compliance_router,
    {
        "generate_mto_blueprint": "generate_mto_blueprint",
        "pricing_estimation": "pricing_estimation",
    },
)

# Wire the MTO path: blueprint → human review → pricing
graph_builder.add_edge("generate_mto_blueprint", "await_human_review")
graph_builder.add_edge("await_human_review", "pricing_estimation")

# Wire the final path: pricing → output compiler → email draft → END
graph_builder.add_edge("pricing_estimation", "output_compiler")
graph_builder.add_edge("output_compiler", "email_draft")
graph_builder.add_edge("email_draft", END)


# ─── Compile with persistent PostgreSQL checkpointer ───
# PostgresSaver stores graph state snapshots in the Supabase PostgreSQL database,
# enabling interrupt/resume across separate serverless function invocations.

# Step 1: Run setup() with a dedicated autocommit connection to create checkpoint tables.
# CREATE INDEX CONCURRENTLY cannot run inside a transaction block, so we use a raw
# psycopg connection with autocommit=True instead of the connection pool.
import psycopg
from api.database.client import database_url

_setup_conn = psycopg.connect(database_url, autocommit=True)
_setup_checkpointer = PostgresSaver(_setup_conn)
# Create checkpoint tables on first run (idempotent — safe to call on every startup)
_setup_checkpointer.setup()
_setup_conn.close()

# Step 2: Create the runtime checkpointer using the connection pool for efficient
# connection reuse across concurrent requests.
checkpointer = PostgresSaver(connection_pool)

# Compile the graph into an executable workflow with persistent state checkpointing
rfp_workflow = graph_builder.compile(checkpointer=checkpointer)
