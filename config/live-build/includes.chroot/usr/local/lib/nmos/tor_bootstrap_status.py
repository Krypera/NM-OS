#!/usr/bin/env python3

import json
from pathlib import Path


READY_FILE = Path("/run/nmos/network-ready")
STATUS_FILE = Path("/run/nmos/network-status.json")


def normalize_status_payload(raw: object) -> dict:
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


def parse_bootstrap_status(status: str) -> tuple[int, str]:
    import re

    progress_match = re.search(r"PROGRESS=(\d+)", status)
    summary_match = re.search(r'SUMMARY="([^"]+)"', status)
    progress = int(progress_match.group(1)) if progress_match else 0
    progress = max(0, min(100, progress))
    summary = summary_match.group(1) if summary_match else "Bootstrapping Tor"
    return progress, summary


def read_status() -> dict:
    if READY_FILE.exists():
        return {"ready": True, "progress": 100, "summary": "Tor is ready", "last_error": ""}

    if STATUS_FILE.exists():
        try:
            return normalize_status_payload(json.loads(STATUS_FILE.read_text(encoding="utf-8")))
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
    return normalize_status_payload({"ready": progress >= 100, "progress": progress, "summary": summary, "last_error": ""})


if __name__ == "__main__":
    print(json.dumps(read_status()))
