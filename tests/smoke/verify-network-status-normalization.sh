#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
sys.path.insert(0, str(root / "apps" / "nmos_common"))
sys.path.insert(0, str(root / "apps" / "nmos_greeter"))
path = root / "apps" / "nmos_greeter" / "nmos_greeter" / "client.py"
spec = importlib.util.spec_from_file_location("nmos_client", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
tor_path = root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py"
tor_spec = importlib.util.spec_from_file_location("nmos_tor_status", tor_path)
tor_module = importlib.util.module_from_spec(tor_spec)
assert tor_spec.loader is not None
tor_spec.loader.exec_module(tor_module)
shared_path = root / "apps" / "nmos_common" / "nmos_common" / "network_status.py"
assert shared_path.exists()
import nmos_common.network_status as shared_module

state = module.normalize_network_status({"ready": True, "progress": "145", "summary": "Ready", "last_error": None})
assert state["ready"] is True
assert state["progress"] == 100
assert state["phase"] == "bootstrap"
assert state["summary"] == "Ready"
assert state["last_error"] == ""

state2 = module.normalize_network_status({"progress": -9})
assert state2["ready"] is False
assert state2["progress"] == 0
assert state2["phase"] == "bootstrap"
assert state2["summary"] == "Waiting for Tor bootstrap"

state_bool = module.normalize_network_status({"ready": "false", "progress": 5, "summary": "Tor"})
assert state_bool["ready"] is False
assert state_bool["progress"] == 5

state3 = module.normalize_network_status(["unexpected"])
assert state3["ready"] is False
assert state3["progress"] == 0
assert state3["phase"] == "bootstrap"
assert state3["last_error"] == "invalid status payload"

assert shared_module.parse_bootstrap_status('NOTICE BOOTSTRAP PROGRESS=42 SUMMARY="Loading"') == (42, "Loading")
assert tor_module.parse_bootstrap_status('NOTICE BOOTSTRAP PROGRESS=42 SUMMARY="Loading"') == (42, "Loading")
assert tor_module.parse_bootstrap_status is shared_module.parse_bootstrap_status
assert module.normalize_network_status is shared_module.normalize_network_status
assert tor_module.normalize_network_status is shared_module.normalize_network_status

with tempfile.TemporaryDirectory() as tmp:
    tmp_root = Path(tmp)
    module.NETWORK_READY_FILE = tmp_root / "network-ready"
    module.NETWORK_STATUS_FILE = tmp_root / "network-status.json"
    tor_module.READY_FILE = tmp_root / "network-ready"
    tor_module.STATUS_FILE = tmp_root / "network-status.json"
    tor_module.STATUS_FILE.write_text('{"ready":"yes","progress":"101","summary":"","last_error":null}', encoding="utf-8")
    tor_state = tor_module.read_status()
    assert tor_state["ready"] is True
    assert tor_state["progress"] == 100
    assert tor_state["summary"] == "Waiting for Tor bootstrap"
    assert tor_state["last_error"] == ""

    client_state = module.read_network_status()
    assert client_state["ready"] is True
    assert client_state["progress"] == 100

    module.NETWORK_READY_FILE.unlink()
    client_state = module.read_network_status()
    assert client_state["ready"] is True
    assert client_state["progress"] == 100

print("Network status normalization checks passed")
PY
