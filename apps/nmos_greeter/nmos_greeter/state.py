from __future__ import annotations

import json
from pathlib import Path

from nmos_common.runtime_state import ensure_runtime_state_path_safe, read_runtime_text, write_runtime_text

STATE_FILE = Path("/run/nmos/greeter-state.json")
STATE_FILE_MODE = 0o660


def ensure_state_path_safe() -> bool:
    try:
        ensure_runtime_state_path_safe(STATE_FILE)
    except OSError:
        return False
    return True


def write_state_payload(payload: str) -> None:
    write_runtime_text(STATE_FILE, payload, mode=STATE_FILE_MODE)


def load_state() -> dict:
    try:
        raw = read_runtime_text(STATE_FILE).strip()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_state(state: dict) -> None:
    write_state_payload(json.dumps(state, indent=2))


def clear_state() -> None:
    write_state_payload("{}\n")
