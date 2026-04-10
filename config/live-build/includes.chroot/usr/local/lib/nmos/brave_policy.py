#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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


def load_mode() -> str:
    if not BOOT_MODE_FILE.exists():
        return "strict"
    try:
        payload = json.loads(BOOT_MODE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return "strict"
    if not isinstance(payload, dict):
        return "strict"
    return str(payload.get("mode", "strict") or "strict")


def brave_feature_enabled() -> bool:
    if not BRAVE_FEATURE_FILE.exists():
        return False
    try:
        for line in BRAVE_FEATURE_FILE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key.strip() == "enabled":
                return value.strip().lower() in {"1", "true", "yes", "on"}
    except OSError:
        return False
    return False


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

    mode = load_mode()
    if mode not in ALLOWED_MODES:
        return deny(f"Brave is disabled in '{mode}' mode. Reboot into Flexible mode to use Brave.")

    if not target.exists():
        print(f"Brave binary not found: {target}", file=sys.stderr)
        return 127

    os.execv(str(target), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
