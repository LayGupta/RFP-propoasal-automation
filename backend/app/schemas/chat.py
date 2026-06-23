from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., description="User's question")
    thread_id: Optional[str] = Field(None, description="Thread ID for RFP context")
