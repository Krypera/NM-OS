#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from nmos_common.runtime_state import write_runtime_json
from nmos_common.system_settings import RUNTIME_SETTINGS_FILE, load_system_settings


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
    write_runtime_json(RUNTIME_SETTINGS_FILE, settings, mode=0o660)
    log(f"NMOS_SETTINGS network_policy={settings['network_policy']}")


if __name__ == "__main__":
    main()
