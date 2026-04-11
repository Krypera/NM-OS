from __future__ import annotations

import json
from pathlib import Path

from nmos_common.config_helpers import parse_bool
from nmos_common.runtime_state import read_runtime_text, write_runtime_json

DEFAULT_UI_LOCALE = "en_US.UTF-8"
DEFAULT_KEYBOARD = "us"
DEFAULT_NETWORK_POLICY = "tor"
SUPPORTED_NETWORK_POLICIES = {"tor", "direct", "offline"}

PERSISTENT_SETTINGS_FILE = Path("/var/lib/nmos/system-settings.json")
RUNTIME_SETTINGS_FILE = Path("/run/nmos/system-settings.json")

DEFAULT_SYSTEM_SETTINGS = {
    "locale": DEFAULT_UI_LOCALE,
    "keyboard": DEFAULT_KEYBOARD,
    "network_policy": DEFAULT_NETWORK_POLICY,
    "allow_brave_browser": False,
}


def normalize_network_policy(value: object, default: str = DEFAULT_NETWORK_POLICY) -> str:
    text = str(value or "").strip().lower()
    if text in SUPPORTED_NETWORK_POLICIES:
        return text
    return default


def normalize_system_settings(payload: object) -> dict:
    raw = payload if isinstance(payload, dict) else {}
    return {
        "locale": str(raw.get("locale", DEFAULT_UI_LOCALE) or DEFAULT_UI_LOCALE),
        "keyboard": str(raw.get("keyboard", DEFAULT_KEYBOARD) or DEFAULT_KEYBOARD),
        "network_policy": normalize_network_policy(raw.get("network_policy", DEFAULT_NETWORK_POLICY)),
        "allow_brave_browser": parse_bool(raw.get("allow_brave_browser"), default=False),
    }


def _read_json_mapping(path: Path) -> dict:
    try:
        payload = json.loads(read_runtime_text(path))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def load_system_settings(
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
) -> dict:
    if persistent_path.exists():
        return normalize_system_settings(_read_json_mapping(persistent_path))
    if runtime_path.exists():
        return normalize_system_settings(_read_json_mapping(runtime_path))
    return dict(DEFAULT_SYSTEM_SETTINGS)


def save_system_settings(
    settings: object,
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    mode: int = 0o660,
) -> dict:
    normalized = normalize_system_settings(settings)
    write_runtime_json(persistent_path, normalized, mode=mode)
    write_runtime_json(runtime_path, normalized, mode=mode)
    return normalized


def network_policy_uses_tor(settings: object) -> bool:
    return normalize_system_settings(settings)["network_policy"] == "tor"


def network_policy_is_offline(settings: object) -> bool:
    return normalize_system_settings(settings)["network_policy"] == "offline"
