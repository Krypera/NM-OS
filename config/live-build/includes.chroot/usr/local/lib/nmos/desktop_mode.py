#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

BOOT_MODE_FILE = Path("/run/nmos/boot-mode.json")
BRAVE_FEATURE_FILE = Path("/etc/nmos/features/brave")
BRAVE_DESKTOP_SOURCE = Path("/usr/share/applications/brave-browser.desktop")
BRAVE_DESKTOP_OVERRIDE = Path.home() / ".local/share/applications/brave-browser.desktop"
MANAGED_MARKER = "X-NMOS-Managed=true"


def load_mode() -> str:
    if not BOOT_MODE_FILE.exists():
        return "strict"
    try:
        data = json.loads(BOOT_MODE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return "strict"
    if not isinstance(data, dict):
        return "strict"
    return str(data.get("mode", "strict") or "strict")


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
    if not BRAVE_FEATURE_FILE.exists():
        remove_override()
        return
    mode = load_mode()
    if mode == "flexible":
        remove_override()
        return
    write_hidden_override()


if __name__ == "__main__":
    main()
