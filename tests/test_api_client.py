"""Unit tests for backend API client and error sanitization."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch
import httpx

import sys
from pathlib import Path

try:
    from front.api_client import call_backend_supervisor_turn
    from front.models import FocusContext, UserContext
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from front.api_client import call_backend_supervisor_turn
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


if __name__ == "__main__":
    unittest.main()
