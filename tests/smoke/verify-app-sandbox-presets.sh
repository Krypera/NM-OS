#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
APPLICATIONS_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/applications.py"

for path in "${CONTROL_CENTER_MAIN}" "${APPLICATIONS_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required app sandbox preset path: ${path}" >&2
        exit 1
    }
done

grep -q 'APP_SANDBOX_PRESET_OPTIONS = (' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define app sandbox preset options." >&2
    exit 1
}

for preset in '"secure"' '"balanced"' '"compatible"'; do
    grep -q "${preset}" "${CONTROL_CENTER_MAIN}" || {
        echo "missing app sandbox preset option: ${preset}" >&2
        exit 1
    }
done

grep -q 'def apply_sandbox_preset' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define app sandbox preset applier." >&2
    exit 1
}

grep -q 'self.set_all_app_overrides(filesystem="none", network="isolated", devices="none")' "${CONTROL_CENTER_MAIN}" || {
    echo "secure app sandbox preset behavior is missing." >&2
    exit 1
}

grep -q 'self.set_all_app_overrides(filesystem="host", network="shared", devices="all")' "${CONTROL_CENTER_MAIN}" || {
    echo "compatible app sandbox preset behavior is missing." >&2
    exit 1
}

grep -q 'self.set_all_app_overrides(filesystem="inherit", network="inherit", devices="inherit")' "${CONTROL_CENTER_MAIN}" || {
    echo "balanced app sandbox preset behavior is missing." >&2
    exit 1
}

grep -q 'def on_apply_sandbox_preset' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define app sandbox preset action handler." >&2
    exit 1
}

grep -q 'Sandbox preset' "${APPLICATIONS_PANEL}" || {
    echo "applications panel does not expose sandbox preset UI copy." >&2
    exit 1
}

echo "App sandbox preset checks passed."
