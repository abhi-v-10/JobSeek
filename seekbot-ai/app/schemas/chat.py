from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from datetime import datetime


class AgentMessage(BaseModel):
    type: Literal[
        "text",
        "jobs",
        "resume_feedback",
        "roadmap",
        "interview",
        "error",
    ]
    content: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool = True
    session_id: str
    message: AgentMessage