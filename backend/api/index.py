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
from api.auth import (
    get_current_user, get_optional_user, UserClaims,
    register_user, login_user, RegisterRequest, LoginRequest, AuthResponse,
)
from api.database.client import supabase_client
from api.rag import engine as rag_engine
from api.scheduler import start_scheduler, stop_scheduler, scout_and_alert


# ─── FastAPI application instance with lifespan for scheduler ───
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """Start cron scheduler on startup, stop on shutdown."""
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(
    title="FMCG RFP Processing API",
    description="Multi-agent LangGraph workflow for RFP analysis, SKU matching, and proposal generation.",
    version="2.0.0",
    lifespan=lifespan,
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
    """Response from the /start endpoint — either paused for review or fully completed."""
    status: str = Field(..., description="Workflow status")
    thread_id: str = Field(..., description="Thread identifier for resuming this workflow")
    blueprint_payload: list[str] = Field(default_factory=list, description="MTO blueprint markdown documents for review")
    matched_skus: list[dict] = Field(default_factory=list, description="All matched SKU recommendations")
    final_proposal_markdown: Optional[str] = Field(None, description="Completed proposal (only when status=COMPLETED_NO_MTO)")
    outreach_email_draft: Optional[str] = Field(None, description="Auto-generated email draft (only when status=COMPLETED_NO_MTO)")


class FinalResponse(BaseModel):
    """Response from the /resume endpoint with the completed proposal."""
    status: str = Field(..., description="Workflow status — always 'COMPLETED'")
    thread_id: str = Field(..., description="Thread identifier for this workflow")
    final_proposal_markdown: str = Field(..., description="The complete compiled markdown proposal document")
    outreach_email_draft: Optional[str] = Field(None, description="Auto-generated bid submission email draft")


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
    user: UserClaims | None = Depends(get_optional_user),
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

    # Step 3.5: Auto-index the RFP text for RAG chatbot retrieval
    # This builds a FAISS index from the document + product catalog so the
    # chatbot can answer questions about the uploaded RFP immediately.
    try:
        rag_engine.build_index_from_text(thread_id, raw_rfp_text)
    except Exception as e:
        import logging
        logging.warning(f"RAG indexing failed (non-fatal): {e}")

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
        "outreach_email_draft": None,
    }

    # Step 5: Stream the workflow and capture interrupt or completion events
    blueprint_payload: list[str] = []
    matched_skus_data: list[dict] = []
    final_markdown: str = ""
    email_draft: str = ""

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

        # Capture the email draft from the email_draft node
        if "email_draft" in event:
            email_draft = event["email_draft"].get("outreach_email_draft", "")

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
        # Save proposal to database for history
        if final_markdown:
            try:
                save_data = {
                    "thread_id": thread_id,
                    "project_name": file.filename or "Untitled Project",
                    "final_markdown": final_markdown,
                }
                if user:
                    save_data["user_id"] = user.user_id
                supabase_client.table("proposals").insert(save_data).execute()
            except Exception as e:
                import logging
                logging.warning(f"Failed to save proposal to history: {e}")

        return StartResponse(
            status="COMPLETED_NO_MTO",
            thread_id=thread_id,
            blueprint_payload=[],
            matched_skus=matched_skus_data,
            final_proposal_markdown=final_markdown,
            outreach_email_draft=email_draft,
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
    email_draft: str = ""

    for event in rfp_workflow.stream(Command(resume=resume_value), config=config):
        # Capture the final compiled proposal from the output compiler node
        if "output_compiler" in event:
            final_markdown = event["output_compiler"].get("final_proposal_markdown", "")
        # Capture the email draft from the email_draft node
        if "email_draft" in event:
            email_draft = event["email_draft"].get("outreach_email_draft", "")

    # Step 4: Validate that we received a compiled output
    if not final_markdown:
        raise HTTPException(
            status_code=500,
            detail="Workflow completed but no final proposal was generated. This may indicate the thread_id does not match a paused workflow.",
        )

    # Save proposal to database for history
    try:
        save_data = {
            "thread_id": request.thread_id,
            "project_name": "MTO Review Project",
            "final_markdown": final_markdown,
        }
        if request.approved_by:
            # Look up user_id from email
            user_result = supabase_client.table("users").select("id").eq("email", request.approved_by).limit(1).execute()
            if user_result.data:
                save_data["user_id"] = user_result.data[0]["id"]
        supabase_client.table("proposals").insert(save_data).execute()
    except Exception as e:
        import logging
        logging.warning(f"Failed to save proposal to history: {e}")

    return FinalResponse(
        status="COMPLETED",
        thread_id=request.thread_id,
        final_proposal_markdown=final_markdown,
        outreach_email_draft=email_draft,
    )


# ─── Health check endpoint for deployment verification ───
@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Simple health check to verify the API is running and responsive."""
    return {"status": "healthy", "service": "fmcg-rfp-api"}


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS — Custom JWT Authentication (replaces Supabase Auth)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=AuthResponse)
async def api_register(request: RegisterRequest) -> AuthResponse:
    """Create a new user account with email + password. Returns a signed JWT."""
    return register_user(request)


@app.post("/api/auth/login", response_model=AuthResponse)
async def api_login(request: LoginRequest) -> AuthResponse:
    """Authenticate with email + password. Returns a signed JWT."""
    return login_user(request)


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


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5: RAG Chatbot
# ═══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    question: str = Field(..., description="User's question")
    thread_id: Optional[str] = Field(None, description="Thread ID for RFP context")


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    """Answer a question using RAG retrieval from uploaded RFP docs + product catalog."""
    try:
        result = rag_engine.ask(request.question, request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/chat/init")
async def chat_init(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
) -> dict:
    """Initialize the RAG index from an uploaded RFP document."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        raw_text = extract_text_from_upload(file_bytes, file.filename or "doc.txt")
        rag_engine.build_index_from_text(thread_id, raw_text)
        return {"status": "indexed", "thread_id": thread_id, "chunks": len(raw_text) // 500}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 6: Executive Analytics Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/analytics")
async def get_analytics(
    user: UserClaims = Depends(get_current_user),
) -> dict:
    """Return aggregated analytics for the dashboard."""
    try:
        # Total proposals
        proposals = supabase_client.table("proposals").select("id, created_at, thread_id, project_name").eq("user_id", user.user_id).execute()
        total_proposals = len(proposals.data or [])

        # Products stats
        products = supabase_client.table("products").select("sku_id, product_name, conductor_material, category, base_price_per_meter, stock_quantity").execute()
        product_list = products.data or []
        total_products = len(product_list)
        total_inventory_value = sum(p["base_price_per_meter"] * p["stock_quantity"] for p in product_list)

        # Material breakdown
        copper_count = sum(1 for p in product_list if p["conductor_material"] == "copper")
        aluminium_count = total_products - copper_count

        # Proposals by day (last 30 days)
        proposals_by_day = {}
        for p in (proposals.data or []):
            day = p["created_at"][:10] if p.get("created_at") else "unknown"
            proposals_by_day[day] = proposals_by_day.get(day, 0) + 1

        proposals_timeline = [
            {"date": k, "count": v}
            for k, v in sorted(proposals_by_day.items())[-30:]
        ]

        # Scout logs
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


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 7: Send Outreach Email via Resend
# ═══════════════════════════════════════════════════════════════════════════════

class SendEmailRequest(BaseModel):
    recipient_email: str = Field(..., description="Recipient email address")
    email_body: str = Field(..., description="Email body text")
    subject: str = Field("FMCG Industrial Solutions — Bid Submission", description="Email subject")


@app.post("/api/send-outreach")
async def send_outreach(request: SendEmailRequest) -> dict:
    """Send an outreach email via Resend API."""
    import resend as resend_lib

    resend_key = os.environ.get("RESEND_API_KEY")
    if not resend_key:
        raise HTTPException(status_code=500, detail="RESEND_API_KEY not configured.")

    resend_lib.api_key = resend_key

    try:
        result = resend_lib.Emails.send({
            "from": "FMCG Industrial Solutions <onboarding@resend.dev>",
            "to": [request.recipient_email],
            "subject": request.subject,
            "text": request.email_body,
        })
        return {"status": "sent", "id": result.get("id", "unknown") if isinstance(result, dict) else str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 8: Scout Logs + Manual Scout Trigger
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/scout-logs")
async def get_scout_logs() -> list[dict]:
    """Fetch recent auto-scout run logs."""
    try:
        result = supabase_client.table("scout_logs").select("*").order("created_at", desc=True).limit(20).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scout logs: {str(e)}")


@app.post("/api/scout-trigger")
async def trigger_scout() -> dict:
    """Manually trigger a scout run (same as the cron job)."""
    try:
        results = scout_and_alert()
        return {"status": "completed", "results_count": len(results), "opportunities": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual scout failed: {str(e)}")


# ─── Local development server ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
