"""Data contracts for the frontend chat interface."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

UserRole = Literal["admin", "resident"]


class UserContext(BaseModel):
    """Authenticated user context passed with every request."""

    uid: str = Field(..., description="Firebase UID or dev ID")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="'admin' or 'resident'")
    unit_code: Optional[str] = Field(
        default=None,
        description="Assigned apartment code (e.g. 'B-504').",
    )


class FocusContext(BaseModel):
    """Conversational entity focus maintained across turns."""

    last_period: Optional[str] = None
    last_unit_code: Optional[str] = None
    active_analytics_thread_id: Optional[str] = None
    pending_clarification_topic: Optional[str] = None


class SupervisorTurnResult(BaseModel):
    """Response returned from the backend agent supervisor."""

    reply: str
    route: str = "direct_response"
    candidate_options: list[str] = Field(default_factory=list)
    chart_file_path: Optional[str] = None
    chart_base64: Optional[str] = None
    table_data: Optional[list[dict[str, Any]]] = None
    step_name: Optional[str] = None
    step_detail: Optional[str] = None
    thread_id: Optional[str] = None
