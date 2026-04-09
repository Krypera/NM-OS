#!/usr/bin/env python3

import json
from pathlib import Path


READY_FILE = Path("/run/nmos/network-ready")
STATUS_FILE = Path("/run/nmos/network-status.json")


def parse_bootstrap_status(status: str) -> tuple[int, str]:
    import re

    progress_match = re.search(r"PROGRESS=(\d+)", status)
    summary_match = re.search(r'SUMMARY="([^"]+)"', status)
    progress = int(progress_match.group(1)) if progress_match else 0
    summary = summary_match.group(1) if summary_match else "Bootstrapping Tor"
    return progress, summary


def read_status() -> dict:
    if READY_FILE.exists():
        return {"ready": True, "progress": 100, "summary": "Tor is ready"}

    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
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
    return {"ready": progress >= 100, "progress": progress, "summary": summary, "last_error": ""}


if __name__ == "__main__":
    print(json.dumps(read_status()))
