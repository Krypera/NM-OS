#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_OUTPUT = Path("/tmp/nmos-recovery-diagnostics.json")

FILES = {
    "runtime_status": Path("/run/nmos/update-engine-status.json"),
    "runtime_health": Path("/run/nmos/update-engine-health.json"),
    "slot_state": Path("/var/lib/nmos/update-engine/slot-state.json"),
    "history": Path("/var/lib/nmos/update-engine/history.json"),
    "boot_intent": Path("/var/lib/nmos/update-engine/boot-intent.json"),
    "persistent_health": Path("/var/lib/nmos/update-engine/health-state.json"),
    "release_manifest": Path("/usr/share/nmos/release-manifest.json"),
}


def read_json(path: Path) -> object:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"path": str(path), "error": str(exc)}


def grubenv_snapshot() -> dict[str, object]:
    command = ["grub-editenv", "/boot/grub/grubenv", "list"]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return {"error": str(exc)}
    if completed.returncode != 0:
        return {"error": (completed.stderr or completed.stdout or f"exit={completed.returncode}").strip()}
    lines = {}
    for raw_line in completed.stdout.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        lines[key.strip()] = value.strip()
    return lines


def main() -> int:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    payload = {
        "collected_at_epoch": int(time.time()),
        "files": {name: read_json(path) for name, path in FILES.items()},
        "grubenv": grubenv_snapshot(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
