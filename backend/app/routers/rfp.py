"""rfp router — /api/process-rfp/* endpoints"""

import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from langgraph.types import Command

from app.schemas.rfp import StartResponse, FinalResponse, ResumeRequest
from app.core.security import UserClaims
from app.core.database import supabase_client
from app.routers.auth import get_optional_user
from app.services.file_parser import extract_text_from_upload
from app.graph.workflow import rfp_workflow
from app.rag import engine as rag_engine

router = APIRouter(tags=["rfp"])
logger = logging.getLogger("rfp_router")


@router.post("/api/process-rfp/start", response_model=StartResponse)
async def start_rfp_processing(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    user: UserClaims | None = Depends(get_optional_user),
) -> StartResponse:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        raw_rfp_text = extract_text_from_upload(file_bytes, file.filename or "document.txt")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    config = {"configurable": {"thread_id": thread_id}}

    try:
        rag_engine.build_index_from_text(thread_id, raw_rfp_text)
    except Exception as e:
        logger.warning(f"RAG indexing failed (non-fatal): {e}")

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

    blueprint_payload: list[str] = []
    matched_skus_data: list[dict] = []
    final_markdown = ""
    email_draft = ""

    for event in rfp_workflow.stream(initial_state, config=config):
        if "__interrupt__" in event:
            interrupt_value = event["__interrupt__"][0].value
            blueprint_payload = interrupt_value.get("blueprints", [])
            matched_skus_data = interrupt_value.get("matched_skus", [])
        if "output_compiler" in event:
            final_markdown = event["output_compiler"].get("final_proposal_markdown", "")
        if "email_draft" in event:
            email_draft = event["email_draft"].get("outreach_email_draft", "")

    if blueprint_payload:
        return StartResponse(
            status="PAUSED_FOR_HUMAN_REVIEW", thread_id=thread_id,
            blueprint_payload=blueprint_payload, matched_skus=matched_skus_data,
        )
    else:
        if final_markdown:
            try:
                save_data = {"thread_id": thread_id, "project_name": file.filename or "Untitled Project", "final_markdown": final_markdown}
                if user:
                    save_data["user_id"] = user.user_id
                supabase_client.table("proposals").insert(save_data).execute()
            except Exception as e:
                logger.warning(f"Failed to save proposal: {e}")

        return StartResponse(
            status="COMPLETED_NO_MTO", thread_id=thread_id,
            blueprint_payload=[], matched_skus=matched_skus_data,
            final_proposal_markdown=final_markdown, outreach_email_draft=email_draft,
        )


@router.post("/api/process-rfp/resume", response_model=FinalResponse)
def resume_rfp_processing(request: ResumeRequest) -> FinalResponse:
    config = {"configurable": {"thread_id": request.thread_id}}
    resume_value = {
        "human_override_notes": request.notes,
        "commodity_volatility_multiplier": request.adjusted_volatility,
    }
    if request.approved_by:
        resume_value["approved_by"] = request.approved_by

    final_markdown = ""
    email_draft = ""

    for event in rfp_workflow.stream(Command(resume=resume_value), config=config):
        if "output_compiler" in event:
            final_markdown = event["output_compiler"].get("final_proposal_markdown", "")
        if "email_draft" in event:
            email_draft = event["email_draft"].get("outreach_email_draft", "")

    if not final_markdown:
        raise HTTPException(status_code=500, detail="Workflow completed but no proposal was generated.")

    try:
        save_data = {"thread_id": request.thread_id, "project_name": "MTO Review Project", "final_markdown": final_markdown}
        if request.approved_by:
            user_result = supabase_client.table("users").select("id").eq("email", request.approved_by).limit(1).execute()
            if user_result.data:
                save_data["user_id"] = user_result.data[0]["id"]
        supabase_client.table("proposals").insert(save_data).execute()
    except Exception as e:
        logger.warning(f"Failed to save proposal: {e}")

    return FinalResponse(
        status="COMPLETED", thread_id=request.thread_id,
        final_proposal_markdown=final_markdown, outreach_email_draft=email_draft,
    )
