#!/usr/bin/env python3

import json
import sys
from pathlib import Path


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
    from nmos_greeter.network_status import normalize_network_status, parse_bootstrap_status
except Exception:
    import re

    def normalize_network_status(raw: object) -> dict:
        if not isinstance(raw, dict):
            return {"ready": False, "progress": 0, "summary": "Waiting for Tor bootstrap", "last_error": "invalid status payload"}

        ready_value = raw.get("ready", False)
        if isinstance(ready_value, bool):
            ready = ready_value
        elif isinstance(ready_value, (int, float)):
            ready = ready_value != 0
        elif isinstance(ready_value, str):
            ready = ready_value.strip().lower() in {"1", "true", "yes", "on"}
        else:
            ready = False
        summary = str(raw.get("summary", "Waiting for Tor bootstrap") or "Waiting for Tor bootstrap")
        last_error = str(raw.get("last_error", "") or "")
        try:
            progress = int(raw.get("progress", 0))
        except (TypeError, ValueError):
            progress = 0
        progress = max(0, min(100, progress))
        return {"ready": ready, "progress": progress, "summary": summary, "last_error": last_error}

    def parse_bootstrap_status(status: str, default_summary: str = "Bootstrapping Tor") -> tuple[int, str]:
        progress_match = re.search(r"PROGRESS=(\d+)", status)
        summary_match = re.search(r'SUMMARY="([^"]+)"', status)
        progress = int(progress_match.group(1)) if progress_match else 0
        progress = max(0, min(100, progress))
        summary = summary_match.group(1) if summary_match else default_summary
        return progress, summary


READY_FILE = Path("/run/nmos/network-ready")
STATUS_FILE = Path("/run/nmos/network-status.json")


def read_status() -> dict:
    if READY_FILE.exists():
        return {"ready": True, "progress": 100, "summary": "Tor is ready", "last_error": ""}

    if STATUS_FILE.exists():
        try:
            return normalize_network_status(json.loads(STATUS_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass

    try:
        from stem.control import Controller

        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            status = controller.get_info("status/bootstrap-phase", "")
    except Exception as exc:
        return {"ready": False, "progress": 0, "summary": "Waiting for Tor control", "last_error": str(exc)}

    progress, summary = parse_bootstrap_status(status)
    return normalize_network_status({"ready": progress >= 100, "progress": progress, "summary": summary, "last_error": ""})


if __name__ == "__main__":
    print(json.dumps(read_status()))
