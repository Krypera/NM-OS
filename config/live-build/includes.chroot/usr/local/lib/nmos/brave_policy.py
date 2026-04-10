#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from nmos_common.config_helpers import load_feature_flag, load_mode

BOOT_MODE_FILE = Path("/run/nmos/boot-mode.json")
BRAVE_FEATURE_FILE = Path("/etc/nmos/features/brave")
ALLOWED_MODES = {"flexible"}


def log_policy_message(message: str) -> None:
    try:
        subprocess.run(
            ["logger", "-t", "nmos-brave-policy", message],
            check=False,
            timeout=2,
        )
    except Exception:
        pass


def brave_feature_enabled() -> bool:
    return load_feature_flag(BRAVE_FEATURE_FILE)


def deny(message: str) -> int:
    print(message, file=sys.stderr)
    log_policy_message(message)
    return 126


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: brave_policy.py <target-binary> [args...]", file=sys.stderr)
        return 2

    target = Path(sys.argv[1])
    args = [str(target), *sys.argv[2:]]

    if not brave_feature_enabled():
        return deny("Brave is not enabled in this NM-OS build.")

    mode = load_mode(BOOT_MODE_FILE)
    if mode not in ALLOWED_MODES:
        return deny(f"Brave is disabled in '{mode}' mode. Reboot into Flexible mode to use Brave.")

    if not target.exists():
        print(f"Brave binary not found: {target}", file=sys.stderr)
        return 127

    os.execv(str(target), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
