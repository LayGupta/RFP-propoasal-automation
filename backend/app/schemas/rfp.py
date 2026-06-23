from typing import Optional
from pydantic import BaseModel, Field


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., description="The thread_id used when starting the workflow")
    adjusted_volatility: float = Field(..., description="Updated commodity volatility multiplier")
    notes: str = Field(..., description="Human reviewer's override notes and comments")
    approved_by: Optional[str] = Field(None, description="Email of the approving manager")


class StartResponse(BaseModel):
    status: str = Field(..., description="Workflow status")
    thread_id: str = Field(..., description="Thread identifier for resuming this workflow")
    blueprint_payload: list[str] = Field(default_factory=list)
    matched_skus: list[dict] = Field(default_factory=list)
    final_proposal_markdown: Optional[str] = Field(None)
    outreach_email_draft: Optional[str] = Field(None)


class FinalResponse(BaseModel):
    status: str = Field(..., description="Workflow status — always 'COMPLETED'")
    thread_id: str
    final_proposal_markdown: str
    outreach_email_draft: Optional[str] = None
