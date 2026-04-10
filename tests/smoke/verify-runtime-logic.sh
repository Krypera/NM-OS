#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_TOOLS_PYTEST="${ROOT_DIR}/.dev-tools/quality/bin/pytest"

if command -v pytest >/dev/null 2>&1; then
    PYTEST_BIN="$(command -v pytest)"
elif [ -x "${DEV_TOOLS_PYTEST}" ]; then
    PYTEST_BIN="${DEV_TOOLS_PYTEST}"
else
    echo "missing required command: pytest" >&2
    exit 1
fi

PYTHONDONTWRITEBYTECODE=1 "${PYTEST_BIN}" -q -p no:cacheprovider "${ROOT_DIR}/tests/python/test_runtime_logic.py"

echo "runtime logic checks passed"
