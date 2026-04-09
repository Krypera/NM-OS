#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_SH="${ROOT_DIR}/build/build.sh"
BUILD_PS1="${ROOT_DIR}/build/build.ps1"
BRAVE_HOOK="${ROOT_DIR}/hooks/optional/050-install-brave-browser.hook.chroot"

[ -f "${BRAVE_HOOK}" ] || {
    echo "optional Brave hook is missing." >&2
    exit 1
}

grep -q 'NMOS_ENABLE_BRAVE' "${BUILD_SH}" || {
    echo "build.sh does not support NMOS_ENABLE_BRAVE optional feature toggle." >&2
    exit 1
}

grep -q 'hooks/optional/050-install-brave-browser.hook.chroot' "${BUILD_SH}" || {
    echo "build.sh does not stage the optional Brave hook." >&2
    exit 1
}

grep -q 'features=' "${BUILD_SH}" || {
    echo "build manifest does not record enabled optional features." >&2
    exit 1
}

grep -q 'EnableBrave' "${BUILD_PS1}" || {
    echo "build.ps1 does not expose the EnableBrave switch." >&2
    exit 1
}

grep -q 'not equivalent to Tor Browser anonymity' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not include the anonymity warning note." >&2
    exit 1
}

echo "Optional Brave feature wiring looks configured."
