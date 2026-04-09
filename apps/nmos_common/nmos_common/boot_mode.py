from __future__ import annotations

import json
from pathlib import Path


MODE_STRICT = "strict"
MODE_FLEXIBLE = "flexible"
MODE_OFFLINE = "offline"
MODE_RECOVERY = "recovery"
MODE_COMPAT = "compat"

SUPPORTED_BOOT_MODES = {
    MODE_STRICT,
    MODE_FLEXIBLE,
    MODE_OFFLINE,
    MODE_RECOVERY,
    MODE_COMPAT,
}

BOOT_MODE_FILE = Path("/run/nmos/boot-mode.json")


def normalize_boot_mode(value: object, default: str = MODE_STRICT) -> str:
    text = str(value or "").strip().lower()
    if text in SUPPORTED_BOOT_MODES:
        return text
    return default


def parse_mode_from_cmdline(cmdline: str, default: str = MODE_STRICT) -> str:
    for token in cmdline.split():
        if token.startswith("nmos.mode="):
            return normalize_boot_mode(token.split("=", 1)[1], default=default)
    return default


def boot_mode_profile(mode: str) -> dict:
    normalized = normalize_boot_mode(mode)
    if normalized == MODE_FLEXIBLE:
        return {
            "mode": MODE_FLEXIBLE,
            "security_profile": "flexible",
            "network_policy": "tor-first",
            "tor_required": True,
            "desktop_entry_policy": "flexible",
            "recovery_mode": False,
            "compat_enabled": False,
        }
    if normalized == MODE_OFFLINE:
        return {
            "mode": MODE_OFFLINE,
            "security_profile": "offline",
            "network_policy": "disabled",
            "tor_required": False,
            "desktop_entry_policy": "strict",
            "recovery_mode": False,
            "compat_enabled": False,
        }
    if normalized == MODE_RECOVERY:
        return {
            "mode": MODE_RECOVERY,
            "security_profile": "recovery",
            "network_policy": "disabled",
            "tor_required": False,
            "desktop_entry_policy": "strict",
            "recovery_mode": True,
            "compat_enabled": False,
        }
    if normalized == MODE_COMPAT:
        return {
            "mode": MODE_COMPAT,
            "security_profile": "strict",
            "network_policy": "tor-first",
            "tor_required": True,
            "desktop_entry_policy": "strict",
            "recovery_mode": False,
            "compat_enabled": True,
        }
    return {
        "mode": MODE_STRICT,
        "security_profile": "strict",
        "network_policy": "tor-first",
        "tor_required": True,
        "desktop_entry_policy": "strict",
        "recovery_mode": False,
        "compat_enabled": False,
    }


def load_boot_mode_profile(path: Path = BOOT_MODE_FILE) -> dict:
    if not path.exists():
        return boot_mode_profile(MODE_STRICT)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return boot_mode_profile(MODE_STRICT)
    if not isinstance(raw, dict):
        return boot_mode_profile(MODE_STRICT)
    return boot_mode_profile(raw.get("mode", MODE_STRICT))
