from __future__ import annotations

import re


DEFAULT_WAITING_SUMMARY = "Waiting for Tor bootstrap"


def as_ready_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def normalize_network_status(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {
            "ready": False,
            "progress": 0,
            "summary": DEFAULT_WAITING_SUMMARY,
            "last_error": "invalid status payload",
        }

    summary = str(raw.get("summary", DEFAULT_WAITING_SUMMARY) or DEFAULT_WAITING_SUMMARY)
    last_error = str(raw.get("last_error", "") or "")
    try:
        progress = int(raw.get("progress", 0))
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))
    return {
        "ready": as_ready_flag(raw.get("ready", False)),
        "progress": progress,
        "summary": summary,
        "last_error": last_error,
    }


def parse_bootstrap_status(status: str, default_summary: str = "Bootstrapping Tor") -> tuple[int, str]:
    progress_match = re.search(r"PROGRESS=(\d+)", status)
    summary_match = re.search(r'SUMMARY="([^"]+)"', status)
    progress = int(progress_match.group(1)) if progress_match else 0
    progress = max(0, min(100, progress))
    summary = summary_match.group(1) if summary_match else default_summary
    return progress, summary
