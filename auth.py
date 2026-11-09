"""Firebase Identity Toolkit authentication and server-side RBAC claim resolution."""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any
import requests

from front.models import UserContext

logger = logging.getLogger("front.auth")

FIREBASE_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
FIREBASE_RESET_PASSWORD_URL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobConfirmationCode"

# Default local development / smoke-test accounts (server-side only; never exposed to client override)
DEFAULT_DEV_ACCOUNTS: dict[str, dict[str, Any]] = {
    "admin@sierraplaza.cl": {
        "uid": "uid_admin_001",
        "password": os.environ.get("DEV_ADMIN_PASSWORD", "SierraPlaza2026!"),
        "role": "admin",
        "unit_code": None,
    },
    "residente504@sierraplaza.cl": {
        "uid": "uid_res_504",
        "password": os.environ.get("DEV_RESIDENT_PASSWORD", "SierraPlaza2026!"),
        "role": "resident",
        "unit_code": "504",
    },
    "residente101@sierraplaza.cl": {
        "uid": "uid_res_101",
        "password": os.environ.get("DEV_RESIDENT_PASSWORD", "SierraPlaza2026!"),
        "role": "resident",
        "unit_code": "101",
    },
}


def _load_server_role_directory() -> dict[str, dict[str, Any]]:
    """Load server-side user role and unit directory from environment or defaults."""
    directory = {k.lower(): dict(v) for k, v in DEFAULT_DEV_ACCOUNTS.items()}
    raw_json = os.environ.get("DEV_USERS_JSON")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                for email, info in parsed.items():
                    if isinstance(info, dict):
                        directory[email.strip().lower()] = info
        except Exception as exc:
            logger.warning("Failed to parse DEV_USERS_JSON: %s", exc)
    return directory


def request_password_reset(
    email: str,
    firebase_api_key: str | None = None,
    http_client: Any | None = None,
) -> tuple[bool, str]:
    """Trigger an official password reset email via Firebase Identity Toolkit.

    Args:
        email: User email requesting reset.
        firebase_api_key: Optional API key override (defaults to FIREBASE_API_KEY env var).
        http_client: Optional HTTP client for testing.

    Returns:
        (success: bool, message: str)
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, "Por favor ingrese un correo electrónico válido."

    api_key = firebase_api_key if firebase_api_key is not None else os.environ.get("FIREBASE_API_KEY")
    if not api_key:
        logger.info("Local dev password reset simulated for '%s'", clean_email)
        return True, "Si el correo está registrado en la Comunidad Sierra Plaza, recibirá un enlace para restablecer su contraseña."

    http_post = http_client.post if http_client is not None else requests.post
    try:
        res = http_post(
            f"{FIREBASE_RESET_PASSWORD_URL}?key={api_key}",
            json={
                "requestType": "PASSWORD_RESET",
                "email": clean_email,
            },
            timeout=5.0,
        )
        if res.status_code == 200:
            return True, "Se ha enviado un correo con las instrucciones para restablecer su contraseña. Por favor revise su bandeja de entrada o spam."
        else:
            err_data = res.json() if res.content else {}
            err_msg = err_data.get("error", {}).get("message", "UNKNOWN_ERROR")
            logger.warning("Firebase password reset failed for '%s': %s", clean_email, err_msg)
            # For security and privacy, avoid revealing if an email exists
            return True, "Si el correo está registrado en la Comunidad Sierra Plaza, recibirá un enlace para restablecer su contraseña."
    except Exception as exc:
        logger.error("Error connecting to Firebase for password reset: %s", exc)
        return False, "Error al procesar la solicitud. Por favor intente más tarde."


def verify_user_credentials(
    username: str,
    password: str,
    firebase_api_key: str | None = None,
    http_client: Any | None = None,
) -> UserContext | None:
    """Verify email/password via Firebase Auth (or server-side dev directory) and return immutable UserContext."""
    email = (username or "").strip().lower()
    if not email or not password:
        return None

    api_key = firebase_api_key if firebase_api_key is not None else os.environ.get("FIREBASE_API_KEY")
    role_directory = _load_server_role_directory()

    # 1. Firebase Identity Toolkit REST verification when FIREBASE_API_KEY is configured
    if api_key:
        http_post = http_client.post if http_client is not None else requests.post
        try:
            res = http_post(
                f"{FIREBASE_SIGNIN_URL}?key={api_key}",
                json={
                    "email": email,
                    "password": password,
                    "returnSecureToken": True,
                },
                timeout=5.0,
            )
            if res.status_code != 200:
                logger.warning("Firebase authentication rejected for email '%s' (HTTP %s)", email, res.status_code)
                return None

            auth_data = res.json()
            uid = auth_data.get("localId") or f"fb_{email}"
            id_token = auth_data.get("idToken")

            # Extract server-side custom claims from Firebase lookup or server role directory
            claims: dict[str, Any] = {}
            if isinstance(auth_data.get("customAttributes"), str):
                try:
                    claims = json.loads(auth_data["customAttributes"])
                except Exception:
                    claims = {}
            elif id_token:
                try:
                    lookup_res = http_post(
                        f"{FIREBASE_LOOKUP_URL}?key={api_key}",
                        json={"idToken": id_token},
                        timeout=5.0,
                    )
                    if lookup_res.status_code == 200:
                        users_list = lookup_res.json().get("users", [])
                        if users_list and isinstance(users_list[0].get("customAttributes"), str):
                            claims = json.loads(users_list[0]["customAttributes"])
                except Exception:
                    claims = {}

            dir_entry = role_directory.get(email, {})
            role = claims.get("role") or dir_entry.get("role")
            unit_code = claims.get("unit_code") or dir_entry.get("unit_code")

            if role not in ("admin", "resident"):
                logger.warning("User '%s' has no valid role claim assigned on server.", email)
                return None

            if role == "resident" and not unit_code:
                logger.warning("Resident '%s' is missing mandatory unit_code claim.", email)
                return None

            return UserContext(
                uid=uid,
                email=email,
                role=role,
                unit_code=unit_code if role == "resident" else None,
            )
        except Exception as exc:
            logger.error("Firebase authentication error for '%s': %s", email, exc)
            return None

    # 2. Offline / Local Dev verification against server-side directory
    account = role_directory.get(email)
    if not account:
        return None

    expected_password = str(account.get("password", ""))
    if not expected_password or not hmac.compare_digest(password, expected_password):
        return None

    role = account.get("role")
    unit_code = account.get("unit_code")
    if role not in ("admin", "resident"):
        return None

    try:
        return UserContext(
            uid=str(account.get("uid") or f"dev_{email}"),
            email=email,
            role=role,
            unit_code=unit_code if role == "resident" else None,
        )
    except ValueError as exc:
        logger.warning("Invalid account configuration for '%s': %s", email, exc)
        return None
