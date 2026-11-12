"""Unit tests for authentication and password reset flows."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock
import requests

import sys
from pathlib import Path

try:
    from front.auth import FIREBASE_RESET_PASSWORD_URL, request_password_reset
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from front.auth import FIREBASE_RESET_PASSWORD_URL, request_password_reset


class TestPasswordReset(unittest.TestCase):
    """Test suite for request_password_reset functionality and endpoint compliance."""

    def test_endpoint_url_uses_official_firebase_send_oob_code(self) -> None:
        """Verify the password reset URL points to Google Identity Toolkit accounts:sendOobCode."""
        self.assertEqual(
            FIREBASE_RESET_PASSWORD_URL,
            "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode",
        )

    def test_invalid_email_formats(self) -> None:
        """Verify invalid or empty email addresses return an error immediately."""
        for invalid_email in ["", "   ", "invalid-email", "noatsign.com"]:
            success, message = request_password_reset(invalid_email)
            self.assertFalse(success)
            self.assertIn("correo electrónico válido", message)

    def test_local_dev_fallback_without_api_key(self) -> None:
        """When no API key is set, returns simulated local dev success."""
        success, message = request_password_reset("residente@sierraplaza.cl", firebase_api_key="")
        self.assertTrue(success)
        self.assertIn("Si el correo está registrado", message)

    def test_firebase_success_200(self) -> None:
        """When Firebase returns 200, sends reset email and returns user instructions."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"email":"residente@sierraplaza.cl"}'
        mock_client.post.return_value = mock_response

        success, message = request_password_reset(
            email="residente@sierraplaza.cl",
            firebase_api_key="test-api-key",
            http_client=mock_client,
        )

        self.assertTrue(success)
        self.assertIn("Se ha enviado un correo", message)
        mock_client.post.assert_called_once_with(
            "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=test-api-key",
            json={
                "requestType": "PASSWORD_RESET",
                "email": "residente@sierraplaza.cl",
            },
            timeout=5.0,
        )

    def test_firebase_client_error_400_maintains_anti_enumeration_privacy(self) -> None:
        """When Firebase returns 400 (e.g. EMAIL_NOT_FOUND), maintain privacy."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error":{"code":400,"message":"EMAIL_NOT_FOUND"}}'
        mock_response.json.return_value = {"error": {"code": 400, "message": "EMAIL_NOT_FOUND"}}
        mock_client.post.return_value = mock_response

        success, message = request_password_reset(
            email="unknown@sierraplaza.cl",
            firebase_api_key="test-api-key",
            http_client=mock_client,
        )

        self.assertTrue(success)
        self.assertIn("Si el correo está registrado", message)

    def test_upstream_non_json_html_error_handled_gracefully(self) -> None:
        """When upstream returns HTML (e.g. 404 or 502), safely parse without JSONDecodeError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b"<html><head><title>404 Not Found</title></head><body>Error</body></html>"
        mock_response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_client.post.return_value = mock_response

        success, message = request_password_reset(
            email="residente@sierraplaza.cl",
            firebase_api_key="test-api-key",
            http_client=mock_client,
        )

        self.assertTrue(success)
        self.assertIn("Si el correo está registrado", message)

    def test_network_connection_error_returns_temporary_failure(self) -> None:
        """When network connection fails, return temporary failure message."""
        mock_client = MagicMock()
        mock_client.post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        success, message = request_password_reset(
            email="residente@sierraplaza.cl",
            firebase_api_key="test-api-key",
            http_client=mock_client,
        )

        self.assertFalse(success)
        self.assertEqual(message, "Error al procesar la solicitud. Por favor intente más tarde.")


if __name__ == "__main__":
    unittest.main()
