#!/usr/bin/env python3

import json
from pathlib import Path

from nmos_common.network_status import normalize_network_status, parse_bootstrap_status
from nmos_common.system_settings import load_system_settings

READY_FILE = Path("/run/nmos/network-ready")
STATUS_FILE = Path("/run/nmos/network-status.json")


def read_status() -> dict:
    settings = load_system_settings()
    policy = str(settings.get("network_policy", "tor"))
    if policy == "offline":
        return normalize_network_status(
            {
                "ready": False,
                "progress": 0,
                "phase": "disabled",
                "summary": "Network is disabled by current settings.",
                "last_error": "",
            }
        )
    if policy == "direct":
        return normalize_network_status(
            {
                "ready": True,
                "progress": 100,
                "phase": "open",
                "summary": "Direct network access is enabled by system settings.",
                "last_error": "",
            }
        )

    if READY_FILE.exists():
        return normalize_network_status(
            {
                "ready": True,
                "progress": 100,
                "phase": "ready",
                "summary": "Tor is ready",
                "last_error": "",
            }
        )

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
        return normalize_network_status(
            {
                "ready": False,
                "progress": 0,
                "phase": "bootstrap",
                "summary": "Waiting for Tor control",
                "last_error": str(exc),
            }
        )

    progress, summary = parse_bootstrap_status(status)
    return normalize_network_status(
        {
            "ready": progress >= 100,
            "progress": progress,
            "phase": "bootstrap",
            "summary": summary,
            "last_error": "",
        }
    )


if __name__ == "__main__":
    print(json.dumps(read_status()))
