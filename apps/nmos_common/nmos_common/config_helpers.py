from __future__ import annotations

import json
from pathlib import Path


def read_assignment_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_mode(path: Path, *, default: str = "strict", key: str = "mode") -> str:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default
    if not isinstance(payload, dict):
        return default
    value = str(payload.get(key, default) or default).strip().lower()
    return value or default
