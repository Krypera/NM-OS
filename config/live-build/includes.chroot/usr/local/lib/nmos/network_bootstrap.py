#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from nmos_common.boot_mode import MODE_OFFLINE, MODE_RECOVERY, load_boot_mode_profile
from nmos_common.network_status import parse_bootstrap_status


READY_DIR = Path("/run/nmos")
READY_FILE = READY_DIR / "network-ready"
STATUS_FILE = READY_DIR / "network-status.json"
TOR_CONTROL_PORT = 9051
BOOTSTRAP_TIMEOUT_SECONDS = 300
SERVICE_START_TIMEOUT_SECONDS = 20


def log(message: str) -> None:
    print(message, flush=True)
    tty = Path("/dev/ttyS0")
    if tty.exists():
        try:
            tty.write_text(message + "\n", encoding="utf-8")
        except OSError:
            pass


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def now_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_status(
    *,
    ready: bool,
    progress: int,
    summary: str,
    phase: str,
    last_error: str = "",
) -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(
            {
                "ready": ready,
                "progress": progress,
                "phase": phase,
                "summary": summary,
                "last_error": last_error,
                "updated_at": now_utc_timestamp(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def write_firewall_rules() -> None:
    import pwd

    tor_uid = pwd.getpwnam("debian-tor").pw_uid
    subprocess.run(["nft", "delete", "table", "inet", "nmosfilter"], check=False)
    rules = f"""
table inet nmosfilter {{
  chain input {{
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
  }}
  chain output {{
    type filter hook output priority 0; policy drop;
    oifname "lo" accept
    ct state established,related accept
    meta skuid 0 udp dport {{ 53, 67, 68, 123 }} accept
    meta skuid {tor_uid} udp dport {{ 53, 123 }} accept
    meta skuid 0 tcp dport 53 accept
    meta skuid {tor_uid} tcp dport 53 accept
    meta skuid {tor_uid} accept
  }}
}}
"""
    subprocess.run(["nft", "-f", "-"], input=rules, text=True, check=True)


def write_offline_firewall_rules() -> None:
    subprocess.run(["nft", "delete", "table", "inet", "nmosfilter"], check=False)
    rules = """
table inet nmosfilter {
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
  }
  chain output {
    type filter hook output priority 0; policy drop;
    oifname "lo" accept
    ct state established,related accept
  }
}
"""
    subprocess.run(["nft", "-f", "-"], input=rules, text=True, check=True)


def nft_table_exists() -> bool:
    return (
        subprocess.run(
            ["nft", "list", "table", "inet", "nmosfilter"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def remove_firewall_gate() -> None:
    # The bootstrap gate is only intended to block user traffic until Tor is
    # ready. Remove the temporary table once readiness is reached.
    if not nft_table_exists():
        return
    subprocess.run(
        ["nft", "delete", "table", "inet", "nmosfilter"],
        check=False,
        capture_output=True,
        text=True,
    )
    if nft_table_exists():
        raise RuntimeError("failed to remove temporary network bootstrap firewall table")


def ensure_online_bootstrap_services() -> None:
    for unit in ("NetworkManager.service", "tor.service", "tor@default.service"):
        try:
            subprocess.run(
                ["systemctl", "start", unit],
                check=False,
                capture_output=True,
                text=True,
                timeout=SERVICE_START_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            log(f"NMOS_NETWORK_WARN timeout starting {unit}")


def wait_for_tor() -> None:
    from stem.control import Controller

    deadline = time.monotonic() + BOOTSTRAP_TIMEOUT_SECONDS
    while True:
        try:
            with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
                controller.authenticate()
                status = controller.get_info("status/bootstrap-phase", "")
        except Exception as exc:
            write_status(
                ready=False,
                progress=0,
                summary="Waiting for Tor control",
                phase="bootstrap",
                last_error=str(exc),
            )
            time.sleep(2)
            if time.monotonic() >= deadline:
                raise RuntimeError("timed out waiting for Tor control port") from exc
            continue

        progress, summary = parse_bootstrap_status(status)
        write_status(ready=progress >= 100, progress=progress, summary=summary, phase="bootstrap")
        if progress >= 100:
            return

        if time.monotonic() >= deadline:
            raise RuntimeError("timed out waiting for Tor bootstrap")
        time.sleep(2)


def mark_ready() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    READY_FILE.write_text("ready\n", encoding="utf-8")
    write_status(ready=True, progress=100, summary="Tor is ready", phase="ready")
    log("NMOS_NETWORK_READY")
    run("systemctl", "start", "nmos-network-ready.target")


def clear_ready_marker() -> None:
    READY_FILE.unlink(missing_ok=True)


def apply_disabled_mode(mode: str) -> None:
    clear_ready_marker()
    write_offline_firewall_rules()
    write_status(
        ready=False,
        progress=0,
        summary=f"Network is disabled by boot mode ({mode}).",
        phase="disabled",
        last_error="",
    )
    log(f"NMOS_NETWORK_DISABLED mode={mode}")


def main() -> None:
    profile = load_boot_mode_profile()
    mode = str(profile.get("mode", "strict"))
    READY_DIR.mkdir(parents=True, exist_ok=True)
    if mode in {MODE_OFFLINE, MODE_RECOVERY}:
        apply_disabled_mode(mode)
        return
    ensure_online_bootstrap_services()
    write_status(ready=False, progress=0, summary="Preparing network policy", phase="policy")
    try:
        write_firewall_rules()
        write_status(ready=False, progress=0, summary="Waiting for Tor bootstrap", phase="bootstrap")
        wait_for_tor()
        remove_firewall_gate()
        mark_ready()
    except Exception as exc:
        write_status(
            ready=False,
            progress=0,
            summary="Network bootstrap failed",
            phase="failed",
            last_error=str(exc),
        )
        log(f"NMOS_NETWORK_FAILED {exc}")
        raise


if __name__ == "__main__":
    main()
