#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from nmos_common.update_engine import run_health_monitor


def log(message: str) -> None:
    print(message, flush=True)
    tty = Path("/dev/ttyS0")
    if tty.exists():
        try:
            tty.write_text(message + "\n", encoding="utf-8")
        except OSError:
            pass


def main() -> None:
    status = run_health_monitor(timeout_seconds=300, poll_interval_seconds=5)
    log(
        "NMOS_UPDATE_HEALTH "
        f"state={status.get('state', 'unknown')} "
        f"pending_slot={status.get('pending_slot', '')} "
        f"active_slot={status.get('active_slot', '')}"
    )


if __name__ == "__main__":
    main()
