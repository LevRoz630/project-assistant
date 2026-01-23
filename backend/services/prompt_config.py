"""Prompt configuration loader for admin customization."""

import os
from pathlib import Path
from typing import Any

import yaml

from .prompts import AIRole

# Path to the config file (relative to backend directory)
CONFIG_FILE = Path(__file__).parent.parent / "prompt_config.yaml"

# Cached config
_config_cache: dict[str, Any] | None = None
_config_mtime: float = 0


def _load_config() -> dict[str, Any]:
    """
    Load the prompt configuration from YAML file.

    Returns:
        Configuration dictionary, or empty dict if file doesn't exist
    """
    global _config_cache, _config_mtime

    if not CONFIG_FILE.exists():
        return {}

    # Check if file was modified
    current_mtime = os.path.getmtime(CONFIG_FILE)
    if _config_cache is not None and current_mtime == _config_mtime:
        return _config_cache

    # Load and cache
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f) or {}
            _config_mtime = current_mtime
            return _config_cache
    except Exception:
        return {}


def get_role_config(role: AIRole) -> dict[str, Any]:
    """
    Get configuration for a specific role.

    Args:
        role: The AI role to get config for

    Returns:
        Configuration dict for the role, or empty dict if not configured
    """
    config = _load_config()
    roles_config = config.get("roles", {})
    return roles_config.get(role.value, {})


def get_custom_instructions(role: AIRole) -> str:
    """
    Get custom instructions for a role.

    Args:
        role: The AI role

    Returns:
        Custom instructions string, or empty string if not configured
    """
    role_config = get_role_config(role)
    return role_config.get("custom_instructions", "")


def is_feature_enabled(role: AIRole, feature: str, default: bool = True) -> bool:
    """
    Check if a feature is enabled for a role.

    Args:
        role: The AI role
        feature: Feature name (e.g., "enable_actions", "enable_search", "enable_fetch")
        default: Default value if not configured

    Returns:
        Whether the feature is enabled
    """
    role_config = get_role_config(role)
    return role_config.get(feature, default)


def get_global_instructions() -> str:
    """
    Get global instructions that apply to all roles.

    Returns:
        Global instructions string, or empty string if not configured
    """
    config = _load_config()
    return config.get("global_instructions", "")


def reload_config() -> None:
    """Force reload of the configuration file."""
    global _config_cache, _config_mtime
    _config_cache = None
    _config_mtime = 0
