#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SYSTEM_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/system.py"
HELP_LAUNCHER="${ROOT_DIR}/config/system-overlay/usr/local/bin/nmos-help"
HELP_DESKTOP_ENTRY="${ROOT_DIR}/config/system-overlay/usr/share/applications/nmos-help.desktop"

for path in "${CONTROL_CENTER_MAIN}" "${SYSTEM_PANEL}" "${HELP_LAUNCHER}" "${HELP_DESKTOP_ENTRY}"; do
    [ -f "${path}" ] || {
        echo "missing required help discoverability path: ${path}" >&2
        exit 1
    }
done

grep -q 'Open User Guides' "${SYSTEM_PANEL}" || {
    echo "system panel does not expose the Open User Guides action." >&2
    exit 1
}

grep -q 'def on_open_help' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not expose the Open Help action handler." >&2
    exit 1
}

grep -q 'def on_open_user_guides' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not expose the Open User Guides handler." >&2
    exit 1
}

grep -q 'def _launch_help_app' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not provide a shared help launcher helper." >&2
    exit 1
}

grep -q '^exec python3 -m nmos_help.main "$@"$' "${HELP_LAUNCHER}" || {
    echo "help launcher does not start the help application module." >&2
    exit 1
}

grep -q '^Exec=/usr/local/bin/nmos-help$' "${HELP_DESKTOP_ENTRY}" || {
    echo "help desktop entry does not point to the expected launcher." >&2
    exit 1
}

echo "Help discoverability checks passed."
