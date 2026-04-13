from __future__ import annotations

import os
from pathlib import Path

from nmos_common.config_helpers import read_assignment_file

DEFAULT_PLATFORM_ADAPTER_FILE = Path("/etc/nmos/platform-adapter.env")

DEFAULT_PLATFORM_VALUES = {
    "tor_user": "debian-tor",
    "gdm_user": "Debian-gdm",
    "settings_admin_group": "sudo",
    "runtime_dir": "/run/nmos",
    "state_dir": "/var/lib/nmos",
}

ENV_KEY_MAP = {
    "NMOS_TOR_USER": "tor_user",
    "NMOS_GDM_USER": "gdm_user",
    "NMOS_SETTINGS_ADMIN_GROUP": "settings_admin_group",
    "NMOS_RUNTIME_DIR": "runtime_dir",
    "NMOS_STATE_DIR": "state_dir",
}


def load_platform_adapter(path: Path = DEFAULT_PLATFORM_ADAPTER_FILE) -> dict[str, str]:
    resolved = dict(DEFAULT_PLATFORM_VALUES)
    try:
        raw = read_assignment_file(path)
    except OSError:
        raw = {}
    for env_key, key in ENV_KEY_MAP.items():
        value = str(os.environ.get(env_key, "")).strip()
        if not value:
            value = str(raw.get(env_key, "")).strip()
        if value:
            resolved[key] = value
    return resolved


def platform_value(key: str, default: str) -> str:
    values = load_platform_adapter()
    value = str(values.get(key, "")).strip()
    return value if value else default


def get_tor_user() -> str:
    return platform_value("tor_user", DEFAULT_PLATFORM_VALUES["tor_user"])


def get_gdm_user() -> str:
    return platform_value("gdm_user", DEFAULT_PLATFORM_VALUES["gdm_user"])


def get_runtime_dir() -> Path:
    return Path(platform_value("runtime_dir", DEFAULT_PLATFORM_VALUES["runtime_dir"]))


def get_state_dir() -> Path:
    return Path(platform_value("state_dir", DEFAULT_PLATFORM_VALUES["state_dir"]))


def get_settings_admin_group() -> str:
    return platform_value("settings_admin_group", DEFAULT_PLATFORM_VALUES["settings_admin_group"])
