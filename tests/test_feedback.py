"""Unit tests for user feedback (thumbs up / down) and comment prompt handling."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from front.app import on_feedback_down, on_feedback_up
from front.models import UserContext


class TestChatFeedbackActions(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying feedback thumbs-up and thumbs-down with comment input."""

    async def test_feedback_down_prompts_comment_and_sends_to_backend(self) -> None:
        """Verify hitting thumbs-down shows a comment box (AskUserMessage) and sends the comment."""
        action = MagicMock()
        action.name = "feedback_down"
        action.payload = {"run_id": "run-uuid-test-456"}
        action.remove = AsyncMock()

        user_ctx = UserContext(
            uid="usr-1",
            email="resident@sierraplaza.cl",
            role="resident",
            unit_code="B-504",
        )

        mock_ask_instance = MagicMock()
        mock_ask_instance.send = AsyncMock(return_value={"output": "El total de agua caliente está errado"})

        with patch("front.app._get_session_user_context", return_value=user_ctx), \
             patch("front.app.cl.AskUserMessage", return_value=mock_ask_instance) as mock_ask_cls, \
             patch("front.app.send_chat_feedback", new_callable=AsyncMock) as mock_send_feedback, \
             patch("front.app.cl.Message") as mock_msg_cls:

            mock_msg_instance = MagicMock()
            mock_msg_instance.send = AsyncMock()
            mock_msg_cls.return_value = mock_msg_instance

            await on_feedback_down(action)

            # 1. Verify comment box (AskUserMessage) was prompted
            mock_ask_cls.assert_called_once()
            mock_ask_instance.send.assert_awaited_once()

            # 2. Verify send_chat_feedback was called with comment and score 0.0
            mock_send_feedback.assert_awaited_once_with(
                run_id="run-uuid-test-456",
                score=0.0,
                value="negative",
                comment="El total de agua caliente está errado",
                user_context=user_ctx,
            )

            # 3. Verify action was removed so buttons don't stay active
            action.remove.assert_awaited_once()

            # 4. Verify user received a confirmation message
            mock_msg_cls.assert_called_once()
            mock_msg_instance.send.assert_awaited_once()

    async def test_feedback_down_clears_task_to_prevent_freezing(self) -> None:
        """Verify emitter.task_end is invoked so UI task running spinner does not get stuck."""
        action = MagicMock()
        action.name = "feedback_down"
        action.payload = {"run_id": "run-uuid-task-end-test"}
        action.remove = AsyncMock()

        user_ctx = UserContext(
            uid="usr-3",
            email="resident@sierraplaza.cl",
            role="resident",
            unit_code="B-504",
        )

        mock_ask_instance = MagicMock()
        mock_ask_instance.send = AsyncMock(return_value={"output": "comentario"})

        mock_emitter = MagicMock()
        mock_emitter.task_end = AsyncMock()

        with patch("front.app._get_session_user_context", return_value=user_ctx), \
             patch("front.app.cl.AskUserMessage", return_value=mock_ask_instance), \
             patch("front.app.cl.context", MagicMock(emitter=mock_emitter)), \
             patch("front.app.send_chat_feedback", new_callable=AsyncMock), \
             patch("front.app.cl.Message", return_value=MagicMock(send=AsyncMock())):

            await on_feedback_down(action)
            mock_emitter.task_end.assert_awaited_once()

    async def test_feedback_up_sends_positive_rating_and_removes_action(self) -> None:
        """Verify hitting thumbs-up sends score 1.0, removes action, and shows confirmation."""
        action = MagicMock()
        action.name = "feedback_up"
        action.payload = {"run_id": "run-uuid-test-123"}
        action.remove = AsyncMock()

        user_ctx = UserContext(
            uid="usr-1",
            email="resident@sierraplaza.cl",
            role="resident",
            unit_code="B-504",
        )

        with patch("front.app._get_session_user_context", return_value=user_ctx), \
             patch("front.app.send_chat_feedback", new_callable=AsyncMock) as mock_send_feedback, \
             patch("front.app.cl.Message") as mock_msg_cls:

            mock_msg_instance = MagicMock()
            mock_msg_instance.send = AsyncMock()
            mock_msg_cls.return_value = mock_msg_instance

            await on_feedback_up(action)

            mock_send_feedback.assert_awaited_once_with(
                run_id="run-uuid-test-123",
                score=1.0,
                value="positive",
                user_context=user_ctx,
            )
            action.remove.assert_awaited_once()
            mock_msg_cls.assert_called_once()
            mock_msg_instance.send.assert_awaited_once()

    async def test_feedback_down_handles_timeout_or_empty_comment(self) -> None:
        """Verify negative feedback is still recorded with comment=None when user skips comment input."""
        action = MagicMock()
        action.name = "feedback_down"
        action.payload = {"run_id": "run-uuid-test-789"}
        action.remove = AsyncMock()

        user_ctx = UserContext(
            uid="usr-2",
            email="admin@sierraplaza.cl",
            role="admin",
        )

        mock_ask_instance = MagicMock()
        mock_ask_instance.send = AsyncMock(return_value=None)  # Simulated timeout

        with patch("front.app._get_session_user_context", return_value=user_ctx), \
             patch("front.app.cl.AskUserMessage", return_value=mock_ask_instance), \
             patch("front.app.send_chat_feedback", new_callable=AsyncMock) as mock_send_feedback, \
             patch("front.app.cl.Message") as mock_msg_cls:

            mock_msg_instance = MagicMock()
            mock_msg_instance.send = AsyncMock()
            mock_msg_cls.return_value = mock_msg_instance

            await on_feedback_down(action)

            mock_send_feedback.assert_awaited_once_with(
                run_id="run-uuid-test-789",
                score=0.0,
                value="negative",
                comment=None,
                user_context=user_ctx,
            )
            action.remove.assert_awaited_once()
            mock_msg_cls.assert_called_once()
            mock_msg_instance.send.assert_awaited_once()
