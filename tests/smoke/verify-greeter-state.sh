#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import tempfile
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
path = root / "apps" / "nmos_greeter" / "nmos_greeter" / "state.py"
spec = importlib.util.spec_from_file_location("nmos_state", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as tmp:
    state_file = Path(tmp) / "greeter-state.json"
    module.STATE_FILE = state_file
    assert module.load_state() == {}
    module.save_state({"locale": "tr_TR.UTF-8", "keyboard": "tr", "allow_offline": True})
    saved = module.load_state()
    assert saved["locale"] == "tr_TR.UTF-8"
    assert saved["keyboard"] == "tr"
    assert saved["allow_offline"] is True
    state_file.write_text('["unexpected", "array"]', encoding="utf-8")
    assert module.load_state() == {}
    module.clear_state()
    assert module.load_state() == {}

print("Greeter state persistence logic checks passed")
PY
