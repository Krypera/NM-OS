from __future__ import annotations

from pathlib import Path

from nmos_common.runtime_state import write_runtime_json


def dump_runtime_state(state_file: Path, state: dict) -> dict:
    write_runtime_json(state_file, state, mode=0o640)
    return state


def build_state_payload(
    *,
    details: dict,
    mapper_open: bool,
    mounted: bool,
    busy: bool,
    operation: str,
    cached_error: str,
    cached_error_reason: str,
    include_cached_error: bool,
) -> dict:
    detail_error = details.get("detail_error", "")
    last_error = detail_error
    reason = str(details.get("reason", "backend_error"))
    if not detail_error and include_cached_error and cached_error:
        last_error = cached_error
        reason = cached_error_reason
    created = bool(details.get("created"))
    can_create = bool(details.get("can_create"))
    return {
        "created": created,
        "unlocked": mapper_open,
        "mapper_open": mapper_open,
        "mounted": mounted,
        "healthy": (created or can_create) and not last_error,
        "busy": busy,
        "operation": operation if busy else "idle",
        "last_error": last_error,
        "can_create": can_create,
        "reason": reason,
        "path": details.get("path", ""),
        "free_bytes": int(details.get("free_bytes", 0) or 0),
        "file_bytes": int(details.get("file_bytes", 0) or 0),
    }
