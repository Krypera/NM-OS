#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from pathlib import Path

from nmos_common.platform_adapter import get_runtime_dir
from nmos_common.runtime_state import write_runtime_json
from nmos_common.system_settings import load_effective_system_settings

JOURNALD_DROPIN_DIR = Path("/etc/systemd/journald.conf.d")
JOURNALD_DROPIN_FILE = JOURNALD_DROPIN_DIR / "90-nmos-logging-policy.conf"
LOGGING_STATUS_FILE = get_runtime_dir() / "logging-policy-status.json"

POLICY_PROFILES = {
    "balanced": {
        "Storage": "persistent",
        "SystemMaxUse": "256M",
        "RuntimeMaxUse": "128M",
        "MaxRetentionSec": "14day",
        "vacuum_time": "14d",
    },
    "minimal": {
        "Storage": "auto",
        "SystemMaxUse": "96M",
        "RuntimeMaxUse": "64M",
        "MaxRetentionSec": "3day",
        "vacuum_time": "3d",
    },
    "sealed": {
        "Storage": "volatile",
        "SystemMaxUse": "32M",
        "RuntimeMaxUse": "32M",
        "MaxRetentionSec": "1day",
        "vacuum_time": "1d",
    },
}


def log(message: str) -> None:
    print(message, flush=True)
    tty = Path("/dev/ttyS0")
    if tty.exists():
        try:
            tty.write_text(message + "\n", encoding="utf-8")
        except OSError:
            pass


def policy_name(settings: dict) -> str:
    value = str(settings.get("logging_policy", "minimal")).strip().lower()
    if value in POLICY_PROFILES:
        return value
    return "minimal"


def render_journald_dropin(profile: str) -> str:
    config = POLICY_PROFILES[profile]
    return (
        "# Managed by NM-OS logging policy service.\n"
        "# Local changes may be overwritten.\n"
        "[Journal]\n"
        f"Storage={config['Storage']}\n"
        f"SystemMaxUse={config['SystemMaxUse']}\n"
        f"RuntimeMaxUse={config['RuntimeMaxUse']}\n"
        f"MaxRetentionSec={config['MaxRetentionSec']}\n"
    )


def run_best_effort(*args: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = completed.stderr.strip() or completed.stdout.strip()
    return completed.returncode == 0, detail


def main() -> None:
    settings = load_effective_system_settings()
    profile = policy_name(settings)
    JOURNALD_DROPIN_DIR.mkdir(parents=True, exist_ok=True)
    JOURNALD_DROPIN_FILE.write_text(render_journald_dropin(profile), encoding="utf-8")

    reload_ok, reload_detail = run_best_effort("systemctl", "kill", "-s", "HUP", "systemd-journald.service", timeout=8)
    vacuum_ok, vacuum_detail = run_best_effort(
        "journalctl",
        f"--vacuum-time={POLICY_PROFILES[profile]['vacuum_time']}",
        timeout=20,
    )

    status = {
        "logging_policy": profile,
        "dropin": str(JOURNALD_DROPIN_FILE),
        "reload_ok": reload_ok,
        "reload_detail": reload_detail,
        "vacuum_ok": vacuum_ok,
        "vacuum_detail": vacuum_detail,
    }
    write_runtime_json(LOGGING_STATUS_FILE, status, mode=0o644)
    log(f"NMOS_LOGGING_POLICY policy={profile} reload_ok={reload_ok} vacuum_ok={vacuum_ok}")


if __name__ == "__main__":
    main()
