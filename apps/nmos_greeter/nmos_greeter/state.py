from __future__ import annotations

import json
import os
from pathlib import Path


STATE_FILE = Path("/run/nmos/greeter-state.json")
STATE_FILE_MODE = 0o660


def ensure_state_path_safe() -> bool:
    try:
        return not STATE_FILE.is_symlink()
    except OSError:
        return False


def write_state_payload(payload: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ensure_state_path_safe():
        raise OSError("greeter state path must not be a symlink")
    fd = os.open(STATE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, STATE_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
    try:
        os.chmod(STATE_FILE, STATE_FILE_MODE)
    except OSError:
        pass


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    if not ensure_state_path_safe():
        return {}
    try:
        raw = STATE_FILE.read_text(encoding="utf-8").strip()
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
