#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 -m py_compile \
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/"*.py \
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/"*.py \
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/"*.py

echo "Python sources compile."

