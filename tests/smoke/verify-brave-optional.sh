#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_SH="${ROOT_DIR}/build/build.sh"
BUILD_PS1="${ROOT_DIR}/build/build.ps1"
DESKTOP_MODE_SCRIPT="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/desktop_mode.py"
AUTOSTART_FILE="${ROOT_DIR}/config/system-overlay/etc/xdg/autostart/nmos-desktop-mode.desktop"
BRAVE_POLICY_SCRIPT="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/brave_policy.py"
OPTIONAL_PACKAGES_FILE="${ROOT_DIR}/config/system-packages/optional-brave.txt"

[ -f "${BRAVE_POLICY_SCRIPT}" ] || {
    echo "Brave policy runtime helper is missing." >&2
    exit 1
}

grep -q 'NMOS_ENABLE_BRAVE' "${BUILD_SH}" || {
    echo "build.sh does not support NMOS_ENABLE_BRAVE optional feature toggle." >&2
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

grep -q 'load_feature_flag' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not use shared feature-flag parsing." >&2
    exit 1
}

grep -q 'load_effective_system_settings' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not read effective system settings." >&2
    exit 1
}

grep -q 'allow_brave_browser' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not respect the Brave visibility setting." >&2
    exit 1
}

grep -q 'Exec=/usr/local/lib/nmos/desktop_mode.py' "${AUTOSTART_FILE}" || {
    echo "desktop mode policy helper is not wired into desktop autostart." >&2
    exit 1
}

grep -q 'load_effective_system_settings' "${BRAVE_POLICY_SCRIPT}" || {
    echo "Brave policy helper does not read effective system settings." >&2
    exit 1
}

grep -q 'Brave is disabled in system settings.' "${BRAVE_POLICY_SCRIPT}" || {
    echo "Brave policy helper does not block launches when settings disable Brave." >&2
    exit 1
}

grep -q 'Brave is unavailable while networking is disabled.' "${BRAVE_POLICY_SCRIPT}" || {
    echo "Brave policy helper does not block launches in offline mode." >&2
    exit 1
}

grep -q '^brave-browser$' "${OPTIONAL_PACKAGES_FILE}" || {
    echo "optional Brave package list is missing brave-browser." >&2
    exit 1
}

echo "Optional Brave feature wiring looks configured."
