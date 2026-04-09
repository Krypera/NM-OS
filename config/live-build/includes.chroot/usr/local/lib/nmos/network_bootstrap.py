#!/usr/bin/env python3

import json
import subprocess
import sys
import time
from pathlib import Path


READY_DIR = Path("/run/nmos")
READY_FILE = READY_DIR / "network-ready"
STATUS_FILE = READY_DIR / "network-status.json"
TOR_CONTROL_PORT = 9051
BOOTSTRAP_TIMEOUT_SECONDS = 300


def discover_repo_greeter_path() -> Path | None:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "apps" / "nmos_greeter"
        if candidate.exists():
            return candidate
    return None


def ensure_greeter_pythonpath() -> None:
    candidates = [Path("/opt/nmos/apps/nmos_greeter")]
    repo_candidate = discover_repo_greeter_path()
    if repo_candidate is not None:
        candidates.append(repo_candidate)
    for candidate in candidates:
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        if candidate_str in sys.path:
            return
        sys.path.insert(0, candidate_str)
        return


ensure_greeter_pythonpath()

try:
    from nmos_greeter.network_status import parse_bootstrap_status
except Exception:
    import re

    def parse_bootstrap_status(status: str, default_summary: str = "Bootstrapping Tor") -> tuple[int, str]:
        progress_match = re.search(r"PROGRESS=(\d+)", status)
        summary_match = re.search(r'SUMMARY="([^"]+)"', status)
        progress = int(progress_match.group(1)) if progress_match else 0
        progress = max(0, min(100, progress))
        summary = summary_match.group(1) if summary_match else default_summary
        return progress, summary


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


def write_status(*, ready: bool, progress: int, summary: str, last_error: str = "") -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(
            {
                "ready": ready,
                "progress": progress,
                "summary": summary,
                "last_error": last_error,
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


def wait_for_tor() -> None:
    from stem.control import Controller

    deadline = time.monotonic() + BOOTSTRAP_TIMEOUT_SECONDS
    while True:
        try:
            with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
                controller.authenticate()
                status = controller.get_info("status/bootstrap-phase", "")
        except Exception as exc:
            write_status(ready=False, progress=0, summary="Waiting for Tor control", last_error=str(exc))
            time.sleep(2)
            if time.monotonic() >= deadline:
                raise RuntimeError("timed out waiting for Tor control port") from exc
            continue

        progress, summary = parse_bootstrap_status(status)
        write_status(ready=progress >= 100, progress=progress, summary=summary)
        if progress >= 100:
            return

        if time.monotonic() >= deadline:
            raise RuntimeError("timed out waiting for Tor bootstrap")
        time.sleep(2)


def mark_ready() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    READY_FILE.write_text("ready\n", encoding="utf-8")
    write_status(ready=True, progress=100, summary="Tor is ready")
    log("NMOS_NETWORK_READY")
    run("systemctl", "start", "nmos-network-ready.target")


def main() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    write_status(ready=False, progress=0, summary="Preparing network policy")
    try:
        write_firewall_rules()
        write_status(ready=False, progress=0, summary="Waiting for Tor bootstrap")
        wait_for_tor()
        remove_firewall_gate()
        mark_ready()
    except Exception as exc:
        write_status(ready=False, progress=0, summary="Network bootstrap failed", last_error=str(exc))
        log(f"NMOS_NETWORK_FAILED {exc}")
        raise


if __name__ == "__main__":
    main()
