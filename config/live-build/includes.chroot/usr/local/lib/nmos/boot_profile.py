#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from nmos_common.boot_mode import BOOT_MODE_FILE, boot_mode_profile, parse_mode_from_cmdline
from nmos_common.runtime_state import write_runtime_json


def log(message: str) -> None:
    print(message, flush=True)
    tty = Path("/dev/ttyS0")
    if tty.exists():
        try:
            tty.write_text(message + "\n", encoding="utf-8")
        except OSError:
            pass


def read_cmdline(path: Path = Path("/proc/cmdline")) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_profile(profile: dict, path: Path = BOOT_MODE_FILE) -> None:
    write_runtime_json(path, profile, mode=0o644)


def main() -> None:
    mode = parse_mode_from_cmdline(read_cmdline())
    profile = boot_mode_profile(mode)
    write_profile(profile)
    log(f"NMOS_BOOT_MODE {profile['mode']}")


if __name__ == "__main__":
    main()
