"""HTTP client adapter to communicate with the Cloud Run Backend service."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable
import httpx

from front.config import CONFIG
from front.models import FocusContext, SupervisorTurnResult, UserContext

logger = logging.getLogger("front.api_client")

# Load Backend URL from active profile config with env override
BACKEND_URL = CONFIG.get("backend", {}).get("url", "http://localhost:8000").rstrip("/")


async def call_backend_supervisor_turn(
    user_message: str,
    user_context: UserContext,
    messages: list[Any],
    focus: FocusContext,
    clarification_choice: str | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[SupervisorTurnResult, list[Any], FocusContext]:
    """Send user message and context to the Backend Cloud Run service over HTTP."""
    if status_callback:
        status_callback("Conectando con el agente analista...")

    payload = {
        "user_message": user_message,
        "user_context": user_context.model_dump(),
        "messages": [
            m if isinstance(m, dict) else getattr(m, "__dict__", str(m))
            for m in messages
        ],
        "focus": focus.model_dump(),
        "clarification_choice": clarification_choice,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{BACKEND_URL}/api/chat/turn", json=payload)
            resp.raise_for_status()
            data = resp.json()

            turn_result = SupervisorTurnResult(**data.get("turn_result", {}))
            updated_messages = data.get("messages", messages + [{"role": "user", "content": user_message}, {"role": "assistant", "content": turn_result.reply}])
            updated_focus = FocusContext(**data.get("focus", focus.model_dump()))

            return turn_result, updated_messages, updated_focus

    except Exception as exc:
        logger.error("Error calling backend service at %s: %s", BACKEND_URL, exc)
        # Graceful fallback response if backend is offline/unreachable
        error_result = SupervisorTurnResult(
            reply=f"⚠️ No pudimos comunicarnos con el servidor analista ({exc}). Por favor, intenta nuevamente en unos momentos.",
            route="direct_response",
            step_name="Error de conexión",
            step_detail="El backend no respondió en el tiempo esperado.",
        )
        return error_result, messages, focus
