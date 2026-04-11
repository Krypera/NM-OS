from __future__ import annotations

import copy
import json
from pathlib import Path

from nmos_common.config_helpers import parse_bool
from nmos_common.platform_adapter import get_runtime_dir, get_state_dir
from nmos_common.runtime_state import read_runtime_text, write_runtime_json

SCHEMA_VERSION = 1

DEFAULT_UI_LOCALE = "en_US.UTF-8"
DEFAULT_KEYBOARD = "us"
DEFAULT_NETWORK_POLICY = "tor"
DEFAULT_SECURITY_PROFILE = "balanced"

SUPPORTED_NETWORK_POLICIES = {"tor", "direct", "offline"}
SUPPORTED_SECURITY_PROFILES = ("relaxed", "balanced", "hardened", "maximum")
SUPPORTED_SANDBOX_DEFAULTS = ("standard", "focused", "strict")
SUPPORTED_DEVICE_POLICIES = ("shared", "prompt", "locked")
SUPPORTED_LOGGING_POLICIES = ("balanced", "minimal", "sealed")
SUPPORTED_THEME_PROFILES = ("nmos-classic", "nmos-night", "nmos-light")
SUPPORTED_UI_ACCENTS = ("amber", "cyan", "mint", "rose")
SUPPORTED_UI_DENSITIES = ("comfortable", "compact")
SUPPORTED_UI_MOTION = ("full", "reduced")

PERSISTENT_SETTINGS_FILE = get_state_dir() / "system-settings.json"
RUNTIME_SETTINGS_FILE = get_runtime_dir() / "system-settings.json"
APPLIED_SETTINGS_FILE = get_runtime_dir() / "applied-system-settings.json"

PROFILE_METADATA = {
    "relaxed": {
        "label": "Relaxed",
        "summary": "More convenience, fewer guards, direct networking by default.",
    },
    "balanced": {
        "label": "Balanced",
        "summary": "Recommended defaults with Tor-first networking and moderate friction.",
    },
    "hardened": {
        "label": "Hardened",
        "summary": "Stricter defaults for daily use with less convenience and tighter policy.",
    },
    "maximum": {
        "label": "Maximum",
        "summary": "Highest practical protection with strong restrictions and offline defaults.",
    },
}

THEME_PROFILE_LABELS = {
    "nmos-classic": "Classic Signal",
    "nmos-night": "Night Console",
    "nmos-light": "Light Grid",
}

ACCENT_LABELS = {
    "amber": "Amber",
    "cyan": "Cyan",
    "mint": "Mint",
    "rose": "Rose",
}

DENSITY_LABELS = {
    "comfortable": "Comfortable",
    "compact": "Compact",
}

MOTION_LABELS = {
    "full": "Full motion",
    "reduced": "Reduced motion",
}

PROFILE_DEFAULTS = {
    "relaxed": {
        "locale": DEFAULT_UI_LOCALE,
        "keyboard": DEFAULT_KEYBOARD,
        "network_policy": "direct",
        "allow_brave_browser": True,
        "sandbox_default": "standard",
        "vault": {
            "enabled": True,
            "auto_lock_minutes": 0,
            "unlock_on_login": False,
        },
        "device_policy": "shared",
        "logging_policy": "balanced",
        "ui_theme_profile": "nmos-classic",
        "ui_accent": "amber",
        "ui_density": "comfortable",
        "ui_motion": "full",
    },
    "balanced": {
        "locale": DEFAULT_UI_LOCALE,
        "keyboard": DEFAULT_KEYBOARD,
        "network_policy": DEFAULT_NETWORK_POLICY,
        "allow_brave_browser": False,
        "sandbox_default": "focused",
        "vault": {
            "enabled": True,
            "auto_lock_minutes": 15,
            "unlock_on_login": False,
        },
        "device_policy": "prompt",
        "logging_policy": "minimal",
        "ui_theme_profile": "nmos-classic",
        "ui_accent": "amber",
        "ui_density": "comfortable",
        "ui_motion": "full",
    },
    "hardened": {
        "locale": DEFAULT_UI_LOCALE,
        "keyboard": DEFAULT_KEYBOARD,
        "network_policy": DEFAULT_NETWORK_POLICY,
        "allow_brave_browser": False,
        "sandbox_default": "strict",
        "vault": {
            "enabled": True,
            "auto_lock_minutes": 5,
            "unlock_on_login": False,
        },
        "device_policy": "locked",
        "logging_policy": "minimal",
        "ui_theme_profile": "nmos-night",
        "ui_accent": "cyan",
        "ui_density": "compact",
        "ui_motion": "reduced",
    },
    "maximum": {
        "locale": DEFAULT_UI_LOCALE,
        "keyboard": DEFAULT_KEYBOARD,
        "network_policy": "offline",
        "allow_brave_browser": False,
        "sandbox_default": "strict",
        "vault": {
            "enabled": True,
            "auto_lock_minutes": 1,
            "unlock_on_login": False,
        },
        "device_policy": "locked",
        "logging_policy": "sealed",
        "ui_theme_profile": "nmos-night",
        "ui_accent": "mint",
        "ui_density": "compact",
        "ui_motion": "reduced",
    },
}

EFFECTIVE_SETTING_KEYS = (
    "locale",
    "keyboard",
    "network_policy",
    "allow_brave_browser",
    "sandbox_default",
    "vault",
    "device_policy",
    "logging_policy",
    "ui_theme_profile",
    "ui_accent",
    "ui_density",
    "ui_motion",
)

REBOOT_REQUIRED_FIELDS = {
    "network_policy",
    "sandbox_default",
    "device_policy",
    "logging_policy",
}


def _normalize_choice(value: object, supported: tuple[str, ...] | set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in supported else default


def normalize_network_policy(value: object, default: str = DEFAULT_NETWORK_POLICY) -> str:
    return _normalize_choice(value, SUPPORTED_NETWORK_POLICIES, default)


def normalize_security_profile(value: object, default: str = DEFAULT_SECURITY_PROFILE) -> str:
    return _normalize_choice(value, SUPPORTED_SECURITY_PROFILES, default)


def normalize_sandbox_default(value: object, default: str = "focused") -> str:
    return _normalize_choice(value, SUPPORTED_SANDBOX_DEFAULTS, default)


def normalize_device_policy(value: object, default: str = "prompt") -> str:
    return _normalize_choice(value, SUPPORTED_DEVICE_POLICIES, default)


def normalize_logging_policy(value: object, default: str = "minimal") -> str:
    return _normalize_choice(value, SUPPORTED_LOGGING_POLICIES, default)


def normalize_theme_profile(value: object, default: str = "nmos-classic") -> str:
    return _normalize_choice(value, SUPPORTED_THEME_PROFILES, default)


def normalize_ui_accent(value: object, default: str = "amber") -> str:
    return _normalize_choice(value, SUPPORTED_UI_ACCENTS, default)


def normalize_ui_density(value: object, default: str = "comfortable") -> str:
    return _normalize_choice(value, SUPPORTED_UI_DENSITIES, default)


def normalize_ui_motion(value: object, default: str = "full") -> str:
    return _normalize_choice(value, SUPPORTED_UI_MOTION, default)


def profile_defaults(profile: str = DEFAULT_SECURITY_PROFILE) -> dict:
    normalized_profile = normalize_security_profile(profile)
    return copy.deepcopy(PROFILE_DEFAULTS[normalized_profile])


def default_system_settings() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_profile": DEFAULT_SECURITY_PROFILE,
        "overrides": {},
        **profile_defaults(DEFAULT_SECURITY_PROFILE),
        "pending_reboot": [],
    }


DEFAULT_SYSTEM_SETTINGS = default_system_settings()


def _normalize_locale(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_keyboard(value: object, default: str) -> str:
    text = str(value or "").strip().lower()
    return text or default


def normalize_vault_settings(value: object, default: dict | None = None) -> dict:
    default_value = copy.deepcopy(default if isinstance(default, dict) else {"enabled": True, "auto_lock_minutes": 15, "unlock_on_login": False})
    raw = value if isinstance(value, dict) else {}
    try:
        auto_lock_minutes = int(raw.get("auto_lock_minutes", default_value["auto_lock_minutes"]))
    except (TypeError, ValueError):
        auto_lock_minutes = int(default_value["auto_lock_minutes"])
    auto_lock_minutes = max(0, min(240, auto_lock_minutes))
    return {
        "enabled": parse_bool(raw.get("enabled"), default=bool(default_value["enabled"])),
        "auto_lock_minutes": auto_lock_minutes,
        "unlock_on_login": parse_bool(raw.get("unlock_on_login"), default=bool(default_value["unlock_on_login"])),
    }


def _normalize_effective_value(key: str, value: object, default: object) -> object:
    if key == "locale":
        return _normalize_locale(value, str(default))
    if key == "keyboard":
        return _normalize_keyboard(value, str(default))
    if key == "network_policy":
        return normalize_network_policy(value, default=str(default))
    if key == "allow_brave_browser":
        return parse_bool(value, default=bool(default))
    if key == "sandbox_default":
        return normalize_sandbox_default(value, default=str(default))
    if key == "vault":
        return normalize_vault_settings(value, default=default if isinstance(default, dict) else None)
    if key == "device_policy":
        return normalize_device_policy(value, default=str(default))
    if key == "logging_policy":
        return normalize_logging_policy(value, default=str(default))
    if key == "ui_theme_profile":
        return normalize_theme_profile(value, default=str(default))
    if key == "ui_accent":
        return normalize_ui_accent(value, default=str(default))
    if key == "ui_density":
        return normalize_ui_density(value, default=str(default))
    if key == "ui_motion":
        return normalize_ui_motion(value, default=str(default))
    raise KeyError(f"unsupported setting key: {key}")


def derive_overrides_for_profile(profile: str, values: object) -> dict:
    normalized_profile = normalize_security_profile(profile)
    base = profile_defaults(normalized_profile)
    raw = values if isinstance(values, dict) else {}
    overrides: dict[str, object] = {}
    for key in EFFECTIVE_SETTING_KEYS:
        if key not in raw:
            continue
        normalized_value = _normalize_effective_value(key, raw.get(key), base[key])
        if normalized_value != base[key]:
            overrides[key] = normalized_value
    return overrides


def _apply_overrides(base: dict, overrides: dict) -> dict:
    effective = copy.deepcopy(base)
    for key, value in overrides.items():
        if key == "vault" and isinstance(value, dict):
            effective[key] = normalize_vault_settings(value, default=effective[key])
        elif key in EFFECTIVE_SETTING_KEYS:
            effective[key] = _normalize_effective_value(key, value, effective[key])
    return effective


def _read_json_mapping(path: Path) -> dict:
    try:
        payload = json.loads(read_runtime_text(path))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _canonicalize_settings(payload: object) -> dict:
    raw = payload if isinstance(payload, dict) else {}
    profile = normalize_security_profile(raw.get("active_profile", DEFAULT_SECURITY_PROFILE))
    base = profile_defaults(profile)

    raw_overrides = {}
    stored_overrides = raw.get("overrides", {})
    if isinstance(stored_overrides, dict):
        raw_overrides.update(stored_overrides)
    use_top_level_as_override_source = not isinstance(stored_overrides, dict) or raw.get("schema_version") != SCHEMA_VERSION
    for key in EFFECTIVE_SETTING_KEYS:
        if key not in raw:
            continue
        if use_top_level_as_override_source or key not in raw_overrides:
            raw_overrides[key] = raw[key]
    overrides = derive_overrides_for_profile(profile, raw_overrides)
    effective = _apply_overrides(base, overrides)
    return {
        "schema_version": SCHEMA_VERSION,
        "active_profile": profile,
        "overrides": overrides,
        **effective,
        "pending_reboot": [],
    }


def extract_effective_settings(settings: object) -> dict:
    normalized = _canonicalize_settings(settings)
    return {
        "active_profile": normalized["active_profile"],
        **{key: copy.deepcopy(normalized[key]) for key in EFFECTIVE_SETTING_KEYS},
    }


def load_applied_system_settings(applied_path: Path = APPLIED_SETTINGS_FILE) -> dict:
    if not applied_path.exists():
        return extract_effective_settings(DEFAULT_SYSTEM_SETTINGS)
    payload = _read_json_mapping(applied_path)
    if not payload:
        return extract_effective_settings(DEFAULT_SYSTEM_SETTINGS)
    effective = extract_effective_settings(payload)
    return effective


def compute_pending_reboot(
    settings: object,
    applied_settings: object | None = None,
    *,
    applied_path: Path = APPLIED_SETTINGS_FILE,
) -> list[str]:
    effective = extract_effective_settings(settings)
    applied = (
        extract_effective_settings(applied_settings)
        if isinstance(applied_settings, dict)
        else load_applied_system_settings(applied_path)
    )
    pending = []
    for key in sorted(REBOOT_REQUIRED_FIELDS):
        if effective.get(key) != applied.get(key):
            pending.append(key)
    return pending


def normalize_system_settings(payload: object, *, applied_path: Path = APPLIED_SETTINGS_FILE) -> dict:
    normalized = _canonicalize_settings(payload)
    normalized["pending_reboot"] = compute_pending_reboot(
        normalized,
        applied_settings=_read_json_mapping(applied_path) if applied_path.exists() else None,
        applied_path=applied_path,
    )
    return normalized


def load_system_settings(
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
) -> dict:
    if persistent_path.exists():
        return normalize_system_settings(_read_json_mapping(persistent_path), applied_path=applied_path)
    if runtime_path.exists():
        return normalize_system_settings(_read_json_mapping(runtime_path), applied_path=applied_path)
    return normalize_system_settings(DEFAULT_SYSTEM_SETTINGS, applied_path=applied_path)


def load_effective_system_settings(
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
) -> dict:
    return extract_effective_settings(
        load_system_settings(
            persistent_path=persistent_path,
            runtime_path=runtime_path,
            applied_path=applied_path,
        )
    )


def save_system_settings(
    settings: object,
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
    mode: int = 0o660,
    update_applied: bool = False,
) -> dict:
    normalized = normalize_system_settings(settings, applied_path=applied_path)
    if update_applied:
        write_runtime_json(applied_path, extract_effective_settings(normalized), mode=mode)
        normalized["pending_reboot"] = []
    write_runtime_json(persistent_path, normalized, mode=mode)
    write_runtime_json(runtime_path, normalized, mode=mode)
    return normalized


def apply_system_profile(
    profile: object,
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
    mode: int = 0o660,
) -> dict:
    normalized_profile = normalize_security_profile(profile)
    payload = {
        "active_profile": normalized_profile,
        "overrides": {},
    }
    return save_system_settings(
        payload,
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
        mode=mode,
    )


def update_system_overrides(
    overrides: object,
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
    mode: int = 0o660,
) -> dict:
    current = load_system_settings(
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
    )
    merged_overrides = dict(current.get("overrides", {}))
    if isinstance(overrides, dict):
        merged_overrides.update(overrides)
    current["overrides"] = merged_overrides
    return save_system_settings(
        current,
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
        mode=mode,
    )


def reset_to_preset(
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
    mode: int = 0o660,
) -> dict:
    current = load_system_settings(
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
    )
    current["overrides"] = {}
    return save_system_settings(
        current,
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
        mode=mode,
    )


def commit_system_settings(
    *,
    persistent_path: Path = PERSISTENT_SETTINGS_FILE,
    runtime_path: Path = RUNTIME_SETTINGS_FILE,
    applied_path: Path = APPLIED_SETTINGS_FILE,
    mode: int = 0o660,
) -> dict:
    current = load_system_settings(
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
    )
    return save_system_settings(
        current,
        persistent_path=persistent_path,
        runtime_path=runtime_path,
        applied_path=applied_path,
        mode=mode,
    )


def network_policy_uses_tor(settings: object) -> bool:
    return extract_effective_settings(settings)["network_policy"] == "tor"


def network_policy_is_offline(settings: object) -> bool:
    return extract_effective_settings(settings)["network_policy"] == "offline"
