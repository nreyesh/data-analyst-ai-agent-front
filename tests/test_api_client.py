"""Unit tests for backend API client and error sanitization."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch
import httpx

import sys
from pathlib import Path

try:
    from front.api_client import call_backend_supervisor_turn, send_chat_feedback
    from front.models import FocusContext, UserContext
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from front.api_client import call_backend_supervisor_turn, send_chat_feedback
    from front.models import FocusContext, UserContext



class TestApiClientSanitization(unittest.IsolatedAsyncioTestCase):
    """Test suite ensuring no sensitive technical details or URLs leak into user messages."""

    async def test_error_reply_is_sanitized_without_leaking_url_or_exception(self) -> None:
        """Ensure connection errors return generic user-friendly messages without internal URLs."""
        user_ctx = UserContext(
            uid="uid_test",
            email="test@sierraplaza.cl",
            role="resident",
            unit_code="101",
        )
        focus = FocusContext()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                message="Client error '404 Not Found' for url 'https://internal-backend.run.app/api/chat/turn'",
                request=httpx.Request("POST", "https://internal-backend.run.app/api/chat/turn"),
                response=httpx.Response(404),
            )

            result, _, _ = await call_backend_supervisor_turn(
                user_message="¿Qué datos tienes?",
                user_context=user_ctx,
                messages=[],
                focus=focus,
            )

            self.assertEqual(
                result.reply,
                "⚠️ No pudimos comunicarnos con el servidor analista. Por favor, intenta nuevamente en unos momentos.",
            )
            # Guarantee no sensitive substrings leak into user-facing text
            self.assertNotIn("404", result.reply)
            self.assertNotIn("run.app", result.reply)
            self.assertNotIn("http", result.reply)
            self.assertNotIn("Client error", result.reply)

    async def test_non_json_401_handled_gracefully(self) -> None:
        """Ensure plain text 401 response (e.g. from Cloud Run proxy) does not crash with JSONDecodeError."""
        user_ctx = UserContext(
            uid="uid_test",
            email="test@sierraplaza.cl",
            role="resident",
            unit_code="101",
        )
        focus = FocusContext()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = httpx.Response(
                401,
                text="The request was not authorized to invoke this service.",
                request=httpx.Request("POST", "https://internal-backend.run.app/api/chat/turn"),
            )

            result, _, _ = await call_backend_supervisor_turn(
                user_message="Hola",
                user_context=user_ctx,
                messages=[],
                focus=focus,
            )

            self.assertEqual(result.step_name, "Sesión expirada")
            self.assertIn("expirado", result.reply)

    async def test_call_backend_supervisor_turn_passes_conversation_id_and_parses_run_id(self) -> None:
        """Verify call_backend_supervisor_turn transmits conversation_id and populates turn_result.run_id."""
        user_ctx = UserContext(
            uid="uid_test",
            email="test@sierraplaza.cl",
            role="resident",
            unit_code="101",
        )
        focus = FocusContext()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = httpx.Response(
                200,
                json={
                    "turn_result": {
                        "reply": "Respuesta correcta",
                        "route": "direct_response",
                        "run_id": "test-run-id-abc",
                    },
                    "messages": [],
                    "focus": {},
                    "conversation_id": "conv-uuid-1111",
                    "run_id": "test-run-id-abc",
                },
                request=httpx.Request("POST", "http://localhost:8000/api/chat/turn"),
            )

            result, _, _ = await call_backend_supervisor_turn(
                user_message="Hola",
                user_context=user_ctx,
                messages=[],
                focus=focus,
                conversation_id="conv-uuid-1111",
            )

            self.assertEqual(result.reply, "Respuesta correcta")
            self.assertEqual(result.run_id, "test-run-id-abc")
            # Verify payload contained conversation_id
            call_kwargs = mock_post.call_args.kwargs
            sent_payload = call_kwargs.get("json", {})
            self.assertEqual(sent_payload.get("conversation_id"), "conv-uuid-1111")

    async def test_send_chat_feedback(self) -> None:
        """Verify send_chat_feedback dispatches POST request with run_id and score."""
        user_ctx = UserContext(
            uid="uid_test",
            email="test@sierraplaza.cl",
            role="resident",
            unit_code="101",
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = httpx.Response(
                200,
                json={"success": True, "run_id": "test-run-123"},
                request=httpx.Request("POST", "http://localhost:8000/api/chat/feedback"),
            )

            ok = await send_chat_feedback(
                run_id="test-run-123",
                score=1.0,
                value="positive",
                comment="Buena respuesta",
                user_context=user_ctx,
            )
            self.assertTrue(ok)
            call_kwargs = mock_post.call_args.kwargs
            self.assertEqual(call_kwargs["json"]["run_id"], "test-run-123")
            self.assertEqual(call_kwargs["json"]["score"], 1.0)



if __name__ == "__main__":
    unittest.main()
