#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import tempfile
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
path = root / "apps" / "nmos_greeter" / "nmos_greeter" / "gdmclient.py"
spec = importlib.util.spec_from_file_location("nmos_gdmclient", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    defaults = tmpdir / "live-user.conf"
    runtime = tmpdir / "username.conf"

    defaults.write_text('LIVE_USERNAME="nmos"\nLIVE_PASSWORD="live"\n', encoding="utf-8")
    runtime.write_text('LIVE_USERNAME="welcome"\n', encoding="utf-8")
    assert module.live_username(defaults_config=defaults, runtime_config=runtime) == "welcome"
    assert module.live_password(defaults_config=defaults) == "live"
    assert module.live_credentials(defaults_config=defaults, runtime_config=runtime) == ("welcome", "live")

    runtime.unlink()
    assert module.live_credentials(defaults_config=defaults, runtime_config=runtime) == ("nmos", "live")

print("Live login configuration checks passed")
PY
