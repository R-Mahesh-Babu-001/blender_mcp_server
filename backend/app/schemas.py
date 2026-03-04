from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    prompt: str
    image_path: str | None = None
    result_path: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentToolCall(BaseModel):
    tool: Literal["generate_mesh", "blender_modify", "finish"]
    args: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    image_path: str | None = None
    model_path: str | None = None


class EventPayload(BaseModel):
    type: str
    job_id: str
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
