"""
index.py — FastAPI Vercel Serverless Gateway Interface

Exposes API endpoints for the RFP processing workflow:
  1. POST /api/process-rfp/start  — Upload RFP document, extract text, run graph until interrupt
  2. POST /api/process-rfp/resume — Resume paused workflow with human review inputs
  3. GET  /api/history             — Fetch saved proposals for the authenticated user
  4. POST /api/scout-tenders       — Agentic web search for tender discovery via Tavily

The FastAPI `app` instance at module scope is auto-detected by Vercel's @vercel/python builder.
"""

import os
import json
from io import BytesIO
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pdfplumber
from docx import Document
from langgraph.types import Command

from api.graph.workflow import rfp_workflow
from api.auth import get_current_user, get_optional_user, UserClaims
from api.database.client import supabase_client


# ─── FastAPI application instance ───
# Vercel's @vercel/python builder detects this `app` object at module scope.
app = FastAPI(
    title="FMCG RFP Processing API",
    description="Multi-agent LangGraph workflow for RFP analysis, SKU matching, and proposal generation.",
    version="1.0.0",
)

# ─── CORS middleware — allow all inbound traffic for development ───
# In production, restrict allow_origins to your frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS — Request and response schemas for type-safe API contracts
# ═══════════════════════════════════════════════════════════════════════════════

# Resume endpoint accepts JSON body (not multipart) since no file upload is needed
class ResumeRequest(BaseModel):
    """Request body for resuming a paused RFP workflow after human review."""
    thread_id: str = Field(..., description="The thread_id used when starting the workflow")
    adjusted_volatility: float = Field(..., description="Updated commodity volatility multiplier (e.g., 1.15)")
    notes: str = Field(..., description="Human reviewer's override notes and comments")
    approved_by: Optional[str] = Field(None, description="Email of the manager who approved the review")


class StartResponse(BaseModel):
    """Response from the /start endpoint when the workflow pauses for human review."""
    status: str = Field(..., description="Workflow status — always 'PAUSED_FOR_HUMAN_REVIEW'")
    thread_id: str = Field(..., description="Thread identifier for resuming this workflow")
    blueprint_payload: list[str] = Field(default_factory=list, description="MTO blueprint markdown documents for review")
    matched_skus: list[dict] = Field(default_factory=list, description="All matched SKU recommendations")


class FinalResponse(BaseModel):
    """Response from the /resume endpoint with the completed proposal."""
    status: str = Field(..., description="Workflow status — always 'COMPLETED'")
    thread_id: str = Field(..., description="Thread identifier for this workflow")
    final_proposal_markdown: str = Field(..., description="The complete compiled markdown proposal document")


# ═══════════════════════════════════════════════════════════════════════════════
# FILE PARSING UTILITY
# Extracts raw text from uploaded PDF, DOCX, or TXT files server-side.
# This eliminates the need for client-side text extraction in the React frontend.
# ═══════════════════════════════════════════════════════════════════════════════
def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """Extract raw text content from an uploaded document file.

    Supports three formats:
      - .pdf — Uses pdfplumber for robust text extraction including tables and complex layouts
      - .docx — Uses python-docx to extract paragraph text from Word documents
      - .txt (fallback) — Decodes raw bytes as UTF-8 text

    Args:
        file_bytes: The raw byte content of the uploaded file.
        filename: Original filename used to determine the file extension.

    Returns:
        The extracted text content as a single string.

    Raises:
        ValueError: If the file is empty or contains no extractable text.
    """
    # Determine file type from the extension (case-insensitive)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extracted_text = ""

    if extension == "pdf":
        # Use pdfplumber for robust PDF text extraction including tables
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        extracted_text = "\n\n".join(pages)

    elif extension in ("docx", "doc"):
        # Use python-docx to extract paragraph text from Word documents
        doc = Document(BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        extracted_text = "\n".join(paragraphs)

    else:
        # Fallback: treat as plain text (e.g., .txt files)
        extracted_text = file_bytes.decode("utf-8", errors="replace")

    # Validate that we actually extracted some content
    if not extracted_text.strip():
        raise ValueError(f"No text could be extracted from the uploaded file '{filename}'. The file may be empty, scanned (image-only), or in an unsupported format.")

    return extracted_text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: Start RFP Processing
# Accepts a multipart form with the RFP document file and a thread_id.
# Extracts text server-side, runs the LangGraph workflow via .stream(),
# and catches the interrupt to return a PAUSED_FOR_HUMAN_REVIEW response
# with the MTO blueprint payload for the React frontend.
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/process-rfp/start", response_model=StartResponse)
async def start_rfp_processing(
    file: UploadFile = File(..., description="RFP document file (PDF, DOCX, or TXT)"),
    thread_id: str = Form(..., description="Unique thread identifier for this workflow run"),
) -> StartResponse:
    """Upload an RFP document and start the multi-agent processing workflow.

    The workflow runs through sales discovery, technical matching, and compliance routing.
    If any item requires custom MTO manufacturing, the workflow pauses at the human review
    node and returns the blueprint payload for frontend display.

    If all items are standard catalog matches, the workflow completes fully and returns
    the final proposal directly (no interrupt).
    """

    # Step 1: Read the uploaded file content into memory
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Step 2: Extract text from the document based on file type
    try:
        raw_rfp_text = extract_text_from_upload(file_bytes, file.filename or "document.txt")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Step 3: Configure the LangGraph thread for state persistence
    config = {"configurable": {"thread_id": thread_id}}

    # Step 4: Initialize the graph state with extracted text and default values
    initial_state = {
        "raw_rfp_content": raw_rfp_text,
        "metadata": {"thread_id": thread_id},
        "extracted_requirements": [],
        "matched_skus": [],
        "mto_blueprints": [],
        "pricing_breakdown": [],
        "commodity_volatility_multiplier": 1.0,
        "human_override_notes": None,
        "final_proposal_markdown": "",
        "approved_by": None,
        "user_id": None,
    }

    # Step 5: Stream the workflow and capture interrupt or completion events
    blueprint_payload: list[str] = []
    matched_skus_data: list[dict] = []
    final_markdown: str = ""

    for event in rfp_workflow.stream(initial_state, config=config):
        # Check if the graph has interrupted at the human review node
        if "__interrupt__" in event:
            # Extract the interrupt payload containing blueprints and SKU data
            interrupt_value = event["__interrupt__"][0].value
            blueprint_payload = interrupt_value.get("blueprints", [])
            matched_skus_data = interrupt_value.get("matched_skus", [])

        # Check if the workflow completed without interrupting (all standard items)
        if "output_compiler" in event:
            final_markdown = event["output_compiler"].get("final_proposal_markdown", "")

    # Step 6: Return appropriate response based on whether an interrupt occurred
    if blueprint_payload:
        # Workflow paused at human review — frontend should display blueprints
        return StartResponse(
            status="PAUSED_FOR_HUMAN_REVIEW",
            thread_id=thread_id,
            blueprint_payload=blueprint_payload,
            matched_skus=matched_skus_data,
        )
    else:
        # Workflow completed without interrupt — all items were standard catalog matches
        return StartResponse(
            status="COMPLETED_NO_MTO",
            thread_id=thread_id,
            blueprint_payload=[],
            matched_skus=matched_skus_data,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: Resume RFP Processing
# Accepts JSON body with the thread_id, adjusted volatility multiplier,
# and human reviewer's notes. Issues a LangGraph Command(resume=...) to
# wake the exact state snapshot, process pricing, and compile the final output.
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/process-rfp/resume", response_model=FinalResponse)
def resume_rfp_processing(request: ResumeRequest) -> FinalResponse:
    """Resume a paused RFP workflow after human review of MTO blueprints.

    Takes the reviewer's adjusted volatility multiplier and notes, then continues
    the workflow through pricing estimation and output compilation.
    """

    # Step 1: Configure with the same thread_id to resume the exact persisted state
    config = {"configurable": {"thread_id": request.thread_id}}

    # Step 2: Build the resume payload matching what await_human_review_node expects
    resume_value = {
        "human_override_notes": request.notes,
        "commodity_volatility_multiplier": request.adjusted_volatility,
    }
    if request.approved_by:
        resume_value["approved_by"] = request.approved_by

    # Step 3: Resume the workflow by passing Command(resume=...) instead of initial state
    # This wakes the graph from the interrupt point and continues downstream nodes
    final_markdown: str = ""

    for event in rfp_workflow.stream(Command(resume=resume_value), config=config):
        # Capture the final compiled proposal from the output compiler node
        if "output_compiler" in event:
            final_markdown = event["output_compiler"].get("final_proposal_markdown", "")

    # Step 4: Validate that we received a compiled output
    if not final_markdown:
        raise HTTPException(
            status_code=500,
            detail="Workflow completed but no final proposal was generated. This may indicate the thread_id does not match a paused workflow.",
        )

    return FinalResponse(
        status="COMPLETED",
        thread_id=request.thread_id,
        final_proposal_markdown=final_markdown,
    )


# ─── Health check endpoint for deployment verification ───
@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Simple health check to verify the API is running and responsive."""
    return {"status": "healthy", "service": "fmcg-rfp-api"}


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: Proposal History
# Fetches all saved proposals belonging to the authenticated user.
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/history")
async def get_proposal_history(
    user: UserClaims = Depends(get_current_user),
) -> list[dict]:
    """Retrieve all saved proposals for the authenticated user, ordered by creation date."""
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch proposal history: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: Agentic Tender Discovery via Tavily
# Uses Tavily web search + ChatGroq to find active infrastructure RFPs.
# ═══════════════════════════════════════════════════════════════════════════════
class ScoutRequest(BaseModel):
    """Request body for tender scouting."""
    query: str = Field(..., description="Search query for finding tenders (e.g., '1100V XLPE cables RFP India')")


@app.post("/api/scout-tenders")
async def scout_tenders(request: ScoutRequest) -> dict:
    """Search the web for active infrastructure RFPs/tenders using Tavily and compile results with ChatGroq."""
    from langchain_groq import ChatGroq
    from langchain_community.tools.tavily_search import TavilySearchResults

    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        raise HTTPException(
            status_code=500,
            detail="TAVILY_API_KEY not configured. Set it in your .env file.",
        )

    try:
        # Step 1: Execute Tavily web search with the user's query
        search_tool = TavilySearchResults(
            max_results=8,
            search_depth="advanced",
        )
        raw_results = search_tool.invoke(request.query)

        # Step 2: Use ChatGroq to analyze and structure the search results
        scout_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

        structuring_prompt = f"""You are a procurement intelligence analyst. Analyze the following web search results about infrastructure tenders and RFPs.

Search Results:
{json.dumps(raw_results, indent=2)}

Extract and return a JSON array of tender opportunities. Each object must have exactly these fields:
- "tender_title": string (the title of the tender/RFP)
- "summary": string (2-3 sentence summary of what the tender requires)
- "issuing_authority": string (the organization issuing the tender)
- "source_url": string (the URL where this tender was found)

If a field cannot be determined, use "Not specified".
Return ONLY the raw JSON array, no markdown formatting or code blocks."""

        response = scout_llm.invoke(structuring_prompt)

        # Step 3: Parse the LLM response into structured JSON
        try:
            # Try to extract JSON from the response
            content = response.content.strip()
            # Remove potential markdown code block wrapping
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            opportunities = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            # Fallback: construct opportunities from raw Tavily results
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


# ─── Local development server ───
# This block only runs when executing the file directly (not via Vercel).
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
