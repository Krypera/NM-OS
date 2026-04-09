#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMON_SH="${ROOT_DIR}/build/lib/common.sh"

grep -q -- "--exclude '__pycache__/'" "${COMMON_SH}" || {
    echo "build staging does not exclude __pycache__ directories." >&2
    exit 1
}

grep -q -- "--exclude '\\*.pyc'" "${COMMON_SH}" || {
    echo "build staging does not exclude .pyc files." >&2
    exit 1
}

grep -q -- "--exclude '\\*.pyo'" "${COMMON_SH}" || {
    echo "build staging does not exclude .pyo files." >&2
    exit 1
}

grep -q "staged live-build tree contains Python cache artifacts" "${COMMON_SH}" || {
    echo "build staging does not fail closed on Python cache artifacts." >&2
    exit 1
}

echo "Build hygiene checks passed"
