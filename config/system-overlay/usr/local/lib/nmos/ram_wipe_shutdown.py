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


def run_checked(*args: str, timeout: int = 20) -> str:
    try:
        completed = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(detail) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(str(exc)) from exc
    return (completed.stderr or completed.stdout or "").strip()


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
    compact_ok = False
    compact_detail = ""
    try:
        compact_detail = run_checked("sysctl", "-w", "vm.compact_memory=1", timeout=10)
        compact_ok = True
    except RuntimeError as exc:
        message = str(exc).lower()
        if (
            "unknown key" in message
            or "cannot stat" in message
            or "invalid argument" in message
            or "no such file" in message
        ):
            compact_ok = True
            compact_detail = f"unsupported kernel knob: {exc}"
        else:
            compact_ok = False
            compact_detail = str(exc)
    swapoff_ok, swapoff_detail = run_best_effort("swapoff", "-a", timeout=120)

    print(
        "NMOS_RAM_WIPE_SHUTDOWN "
        f"mode={mode} sync_ok={sync_ok} drop_ok={drop_ok} compact_ok={compact_ok} swapoff_ok={swapoff_ok} "
        f"sync_detail={sync_detail!r} drop_detail={drop_detail!r} compact_detail={compact_detail!r} swapoff_detail={swapoff_detail!r}",
        flush=True,
    )


if __name__ == "__main__":
    main()
