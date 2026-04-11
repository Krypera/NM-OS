#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import tempfile
import sys
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
sys.path.insert(0, str(root / "apps" / "nmos_common"))
path = root / "apps" / "nmos_greeter" / "nmos_greeter" / "state.py"
source = path.read_text(encoding="utf-8")
spec = importlib.util.spec_from_file_location("nmos_state", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

assert "ensure_state_path_safe" in source
assert "write_state_payload" in source
assert "write_runtime_text" in source
assert "read_runtime_text" in source
assert "STATE_FILE_MODE = 0o660" in source

with tempfile.TemporaryDirectory() as tmp:
    state_file = Path(tmp) / "greeter-state.json"
    module.STATE_FILE = state_file
    assert module.load_state() == {}
    module.save_state(
        {
            "locale": "es_ES.UTF-8",
            "keyboard": "tr",
            "network_policy": "direct",
            "allow_brave_browser": True,
        }
    )
    saved = module.load_state()
    assert saved["locale"] == "es_ES.UTF-8"
    assert saved["keyboard"] == "tr"
    assert saved["network_policy"] == "direct"
    assert saved["allow_brave_browser"] is True
    state_file.write_text('["unexpected", "array"]', encoding="utf-8")
    assert module.load_state() == {}
    module.clear_state()
    assert module.load_state() == {}

print("Greeter state persistence logic checks passed")
PY
