#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from nmos_common.system_settings import (
    APPLIED_SETTINGS_FILE,
    RUNTIME_SETTINGS_FILE,
    load_system_settings,
    save_system_settings,
)


def log(message: str) -> None:
    print(message, flush=True)
    tty = Path("/dev/ttyS0")
    if tty.exists():
        try:
            tty.write_text(message + "\n", encoding="utf-8")
        except OSError:
            pass


def main() -> None:
    settings = load_system_settings()
    save_system_settings(settings, runtime_path=RUNTIME_SETTINGS_FILE, applied_path=APPLIED_SETTINGS_FILE, update_applied=True)
    log(f"NMOS_SETTINGS profile={settings['active_profile']} network_policy={settings['network_policy']}")


if __name__ == "__main__":
    main()
