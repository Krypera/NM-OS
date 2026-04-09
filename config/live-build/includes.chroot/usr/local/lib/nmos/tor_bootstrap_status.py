#!/usr/bin/env python3

import json
from pathlib import Path

from nmos_common.network_status import normalize_network_status, parse_bootstrap_status


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
