#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
paths = [
    *sorted((root / "apps" / "nmos_greeter" / "nmos_greeter").glob("*.py")),
    *sorted((root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage").glob("*.py")),
    *sorted((root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos").glob("*.py")),
]
for path in paths:
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
PY

echo "Python sources compile."
