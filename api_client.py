"""HTTP client adapter to communicate with the Cloud Run Backend service."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable
import httpx

from front.auth import clear_user_id_token, get_user_id_token
from front.config import CONFIG
from front.models import FocusContext, SupervisorTurnResult, UserContext

logger = logging.getLogger("front.api_client")


def get_backend_url() -> str:
    """Return backend URL checking environment first, then profile config."""
    env_override = os.environ.get("BACKEND_URL") or os.environ.get("BACKEND_API_URL")
    if env_override:
        return env_override.rstrip("/")
    return CONFIG.get("backend", {}).get("url", "http://localhost:8000").rstrip("/")


# Default Backend URL evaluated on module load
BACKEND_URL = get_backend_url()


async def call_backend_supervisor_turn(
    user_message: str,
    user_context: UserContext,
    messages: list[Any],
    focus: FocusContext,
    clarification_choice: str | None = None,
    status_callback: Callable[[str], None] | None = None,
    id_token: str | None = None,
) -> tuple[SupervisorTurnResult, list[Any], FocusContext]:
    """Send user message, context, and server-side Bearer token to the Backend Cloud Run service over HTTP."""
    if status_callback:
        status_callback("Conectando con el agente analista...")

    payload = {
        "user_message": user_message,
        "user_context": user_context.model_dump(),
        "messages": [
            m
            if isinstance(m, dict)
            else {"role": "assistant" if getattr(m, "type", "") == "ai" else "user", "content": getattr(m, "content", str(m))}
            for m in messages
        ],
        "focus": focus.model_dump(),
        "clarification_choice": clarification_choice,
    }

    token = id_token if id_token is not None else get_user_id_token(user_context.uid)
    if not token:
        token = f"dev-token:{user_context.uid}:{user_context.email}:{user_context.role}:{user_context.unit_code or ''}"

    headers = {"Authorization": f"Bearer {token}"}
    backend_url = get_backend_url()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{backend_url}/api/chat/turn",
                json=payload,
                headers=headers,
            )

            if resp.status_code == 401:
                clear_user_id_token(user_context.uid)
                detail: dict[str, Any] = {}
                if resp.content:
                    try:
                        parsed = resp.json()
                        detail = parsed.get("detail", {}) if isinstance(parsed, dict) else {}
                    except Exception:
                        pass
                msg = (
                    detail.get("message")
                    if isinstance(detail, dict)
                    else "🔒 Tu sesión ha expirado. Por favor, vuelve a iniciar sesión para continuar."
                )
                expired_result = SupervisorTurnResult(
                    reply=msg or "🔒 Tu sesión ha expirado. Por favor, vuelve a iniciar sesión para continuar.",
                    route="direct_response",
                    step_name="Sesión expirada",
                    step_detail="Se requiere volver a iniciar sesión (HTTP 401).",
                )
                return expired_result, messages, focus

            if resp.status_code == 403:
                detail = {}
                if resp.content:
                    try:
                        parsed = resp.json()
                        detail = parsed.get("detail", {}) if isinstance(parsed, dict) else {}
                    except Exception:
                        pass
                if isinstance(detail, dict):
                    msg = detail.get("message") or (
                        f"⛔ **Cuenta bloqueada por 24 horas.**\n\n"
                        f"- **Motivo**: {detail.get('reason', 'Violación de seguridad')}\n"
                        f"- **Bloqueo vigente hasta**: `{detail.get('blocked_until', '24h')}`"
                    )
                else:
                    msg = f"⛔ **Acceso bloqueado por 24 horas**: {detail}"
                blocked_result = SupervisorTurnResult(
                    reply=msg,
                    route="direct_response",
                    step_name="Cuenta bloqueada (24h)",
                    step_detail="Acceso restringido por políticas de seguridad (HTTP 403).",
                )
                return blocked_result, messages, focus

            resp.raise_for_status()
            data = resp.json()

            turn_result = SupervisorTurnResult(**data.get("turn_result", {}))
            updated_messages = data.get(
                "messages",
                messages
                + [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": turn_result.reply},
                ],
            )
            updated_focus = FocusContext(**data.get("focus", focus.model_dump()))

            return turn_result, updated_messages, updated_focus

    except Exception as exc:
        logger.error("Error calling backend service at %s: %s", backend_url, exc)
        error_result = SupervisorTurnResult(
            reply="⚠️ No pudimos comunicarnos con el servidor analista. Por favor, intenta nuevamente en unos momentos.",
            route="direct_response",
            step_name="Error de conexión",
            step_detail="El backend no respondió en el tiempo esperado.",
        )
        return error_result, messages, focus
