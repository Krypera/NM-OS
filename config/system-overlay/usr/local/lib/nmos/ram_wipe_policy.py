#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from pathlib import Path

from nmos_common.platform_adapter import get_runtime_dir
from nmos_common.runtime_state import write_runtime_json
from nmos_common.system_settings import load_effective_system_settings

GRUB_DROPIN_DIR = Path("/etc/default/grub.d")
GRUB_DROPIN_FILE = GRUB_DROPIN_DIR / "90-nmos-ram-wipe.cfg"
STATUS_FILE = get_runtime_dir() / "ram-wipe-status.json"

PROFILE_CMDLINE_FLAGS = {
    "off": [],
    "balanced": ["init_on_free=1"],
    "strict": ["init_on_alloc=1", "init_on_free=1", "page_poison=1", "slub_debug=P"],
}


def policy_name(settings: dict) -> str:
    value = str(settings.get("ram_wipe_mode", "balanced")).strip().lower()
    if value in PROFILE_CMDLINE_FLAGS:
        return value
    return "balanced"


def render_grub_dropin(profile: str) -> str:
    flags = " ".join(PROFILE_CMDLINE_FLAGS[profile]).strip()
    if not flags:
        return (
            "# Managed by NM-OS RAM wipe policy service.\n"
            "# RAM wipe mode is off; no kernel memory scrubbing flags are forced.\n"
        )
    return (
        "# Managed by NM-OS RAM wipe policy service.\n"
        "# Enables kernel-level memory init/poison flags for stronger post-use memory hygiene.\n"
        f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {flags}"\n'
    )


def run_best_effort(*args: str, timeout: int = 30) -> tuple[bool, str]:
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
    GRUB_DROPIN_DIR.mkdir(parents=True, exist_ok=True)
    GRUB_DROPIN_FILE.write_text(render_grub_dropin(profile), encoding="utf-8")

    update_ok, update_detail = run_best_effort("update-grub", timeout=90)
    status = {
        "ram_wipe_mode": profile,
        "dropin": str(GRUB_DROPIN_FILE),
        "kernel_flags": PROFILE_CMDLINE_FLAGS[profile],
        "update_grub_ok": update_ok,
        "update_grub_detail": update_detail,
        "reboot_required": True,
    }
    write_runtime_json(STATUS_FILE, status, mode=0o644)
    print(f"NMOS_RAM_WIPE mode={profile} update_grub_ok={update_ok}", flush=True)


if __name__ == "__main__":
    main()
