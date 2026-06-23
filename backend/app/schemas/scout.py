from pydantic import BaseModel, Field


class ScoutRequest(BaseModel):
    query: str = Field(..., description="Search query for finding tenders")


class SendEmailRequest(BaseModel):
    recipient_email: str = Field(..., description="Recipient email address")
    email_body: str = Field(..., description="Email body text")
    subject: str = Field("FMCG Industrial Solutions — Bid Submission", description="Email subject")
