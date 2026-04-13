#!/usr/bin/env python3

from __future__ import annotations

import subprocess

from nmos_common.system_settings import load_effective_system_settings

ENABLED_RAM_WIPE_MODES = {"balanced", "strict"}


def run_best_effort(*args: str, timeout: int = 20) -> tuple[bool, str]:
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


def ram_wipe_mode() -> str:
    settings = load_effective_system_settings()
    return str(settings.get("ram_wipe_mode", "balanced")).strip().lower()


def main() -> None:
    mode = ram_wipe_mode()
    if mode not in ENABLED_RAM_WIPE_MODES:
        print(f"NMOS_RAM_WIPE_SHUTDOWN mode={mode} skipped=true", flush=True)
        return

    sync_ok, sync_detail = run_best_effort("sync", timeout=10)
    drop_ok, drop_detail = run_best_effort("sysctl", "-w", "vm.drop_caches=3", timeout=10)
    compact_ok, compact_detail = run_best_effort("sysctl", "-w", "vm.compact_memory=1", timeout=10)
    swapoff_ok, swapoff_detail = run_best_effort("swapoff", "-a", timeout=20)

    print(
        "NMOS_RAM_WIPE_SHUTDOWN "
        f"mode={mode} sync_ok={sync_ok} drop_ok={drop_ok} compact_ok={compact_ok} swapoff_ok={swapoff_ok} "
        f"sync_detail={sync_detail!r} drop_detail={drop_detail!r} compact_detail={compact_detail!r} swapoff_detail={swapoff_detail!r}",
        flush=True,
    )


if __name__ == "__main__":
    main()
