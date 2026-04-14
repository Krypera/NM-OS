#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_TOOLS_PYTEST="${ROOT_DIR}/.dev-tools/quality/bin/pytest"

PYTEST_CMD=()
if command -v pytest >/dev/null 2>&1; then
    PYTEST_CMD=("$(command -v pytest)")
elif [ -x "${DEV_TOOLS_PYTEST}" ]; then
    PYTEST_CMD=("${DEV_TOOLS_PYTEST}")
elif command -v python3 >/dev/null 2>&1 && python3 -m pytest --version >/dev/null 2>&1; then
    PYTEST_CMD=("python3" "-m" "pytest")
else
    echo "missing required command: pytest (or python3 -m pytest)" >&2
    exit 1
fi

PYTHONDONTWRITEBYTECODE=1 "${PYTEST_CMD[@]}" -q -p no:cacheprovider "${ROOT_DIR}/tests/python/test_compile_sources.py"

echo "Python sources compile."
