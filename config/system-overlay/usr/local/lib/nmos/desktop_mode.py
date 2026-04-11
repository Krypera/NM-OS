#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from nmos_common.config_helpers import load_feature_flag
from nmos_common.system_settings import load_effective_system_settings

BRAVE_FEATURE_FILE = Path("/etc/nmos/features/brave")
BRAVE_DESKTOP_SOURCE = Path("/usr/share/applications/brave-browser.desktop")
BRAVE_DESKTOP_OVERRIDE = Path.home() / ".local/share/applications/brave-browser.desktop"
MANAGED_MARKER = "X-NMOS-Managed=true"


def remove_override() -> None:
    if BRAVE_DESKTOP_OVERRIDE.exists():
        try:
            text = BRAVE_DESKTOP_OVERRIDE.read_text(encoding="utf-8")
        except OSError:
            return
        if MANAGED_MARKER in text:
            BRAVE_DESKTOP_OVERRIDE.unlink(missing_ok=True)


def write_hidden_override() -> None:
    if not BRAVE_DESKTOP_SOURCE.exists():
        return
    BRAVE_DESKTOP_OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
    lines = BRAVE_DESKTOP_SOURCE.read_text(encoding="utf-8").splitlines()
    filtered = [
        line
        for line in lines
        if not line.startswith("NoDisplay=") and not line.startswith("Hidden=") and line != MANAGED_MARKER
    ]
    filtered.append("NoDisplay=true")
    filtered.append("Hidden=true")
    filtered.append(MANAGED_MARKER)
    BRAVE_DESKTOP_OVERRIDE.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def main() -> None:
    if not BRAVE_DESKTOP_SOURCE.exists():
        remove_override()
        return
    brave_enabled = load_feature_flag(BRAVE_FEATURE_FILE)
    settings = load_effective_system_settings()
    allow_brave = bool(settings.get("allow_brave_browser", False))
    offline = str(settings.get("network_policy", "tor")) == "offline"
    if brave_enabled and allow_brave and not offline:
        remove_override()
        return
    write_hidden_override()


if __name__ == "__main__":
    main()
