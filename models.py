"""Data contracts for the frontend chat interface, synchronized with backend/app/agent/state.py."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

UserRole = Literal["admin", "resident"]
SupervisorRoute = Literal[
    "lookup_unit_bill",
    "lookup_building_summary",
    "lookup_spend_evolution",
    "check_system_status",
    "run_deep_financial_analysis",
    "clarify_intent",
    "direct_response",
]
KnowledgeDomain = Literal["building", "unit", "cross_domain"]


class UserContext(BaseModel):
    """Immutable authenticated user context passed with every request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uid: str = Field(..., min_length=1, description="Firebase UID or dev ID")
    email: str = Field(..., min_length=3, description="User email")
    role: UserRole = Field(..., description="'admin' or 'resident'")
    unit_code: Optional[str] = Field(
        default=None,
        description="Assigned apartment code (e.g. 'B-504'). Mandatory when role == 'resident'.",
    )

    @model_validator(mode="after")
    def validate_resident_unit(self) -> "UserContext":
        if self.role == "resident" and (not self.unit_code or not self.unit_code.strip()):
            raise ValueError("Resident user context requires a non-empty 'unit_code'.")
        return self


class FocusContext(BaseModel):
    """Conversational entity focus maintained across turns."""

    model_config = ConfigDict(extra="ignore")

    last_domain: Optional[Literal["building", "unit", "cross_domain", "system"]] = None
    last_unit: Optional[str] = None
    last_period: Optional[str] = None
    last_concept: Optional[str] = None
    last_route: Optional[str] = None
    active_analytics_thread_id: Optional[str] = None
    pending_clarification_query: Optional[str] = None
    pending_clarification_route: Optional[SupervisorRoute] = None


class SupervisorTurnResult(BaseModel):
    """Response returned from the backend agent supervisor."""

    model_config = ConfigDict(extra="ignore")

    reply: str
    route: str = "direct_response"
    step_name: Optional[str] = None
    step_detail: Optional[str] = None
    chart_file_path: Optional[str] = None
    chart_base64: Optional[str] = None
    table_data: Optional[list[dict[str, Any]]] = None
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    candidate_options: list[str] = Field(default_factory=list)
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    focus: FocusContext = Field(default_factory=FocusContext)

    security_violation_type: Optional[str] = None
    security_violation_reason: Optional[str] = None
