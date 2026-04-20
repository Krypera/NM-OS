#!/usr/bin/env bash

set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
python3 - <<'PY'
from __future__ import annotations

import json
import sys

try:
    from nmos_common.update_engine import rollback_to_previous_slot
except Exception as exc:
    print(f"Unable to import NM-OS update engine: {exc}", file=sys.stderr)
    sys.exit(1)

result = rollback_to_previous_slot(reason="recovery")
print(json.dumps(result, indent=2))
PY
else
    echo "python3 is required to trigger NM-OS recovery rollback." >&2
    exit 1
fi
