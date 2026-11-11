"""Application configuration loader with environment profile support (dev, prod)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
import yaml

logger = logging.getLogger("front.config")

_PROFILE_DIR = Path(__file__).resolve().parent / "profile"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dictionary into base dictionary."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_profile_config() -> dict[str, Any]:
    """Load base application.yaml and merge the active environment profile (dev, prod)."""
    env = os.environ.get("ENVIRONMENT", "dev").strip().lower()

    # 1. Load base configuration
    base_file = _PROFILE_DIR / "application.yaml"
    config: dict[str, Any] = {}
    if base_file.is_file():
        with open(base_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # 2. Merge environment-specific profile
    env_file = _PROFILE_DIR / f"application-{env}.yaml"
    if env_file.is_file():
        with open(env_file, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, env_config)
            logger.info("Loaded profile: application-%s.yaml", env)
    else:
        logger.warning("No profile found for environment '%s'. Using defaults.", env)

    # 3. Environment Variable Overrides (Highest Precedence)
    # Allows Cloud Run env vars to override YAML values if needed
    backend_env_url = os.environ.get("BACKEND_URL") or os.environ.get("BACKEND_API_URL")
    if backend_env_url:
        config.setdefault("backend", {})["url"] = backend_env_url.rstrip("/")

    return config


# Global active configuration singleton
CONFIG = load_profile_config()
