#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SECURITY_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/security.py"

for path in "${CONTROL_CENTER_MAIN}" "${SECURITY_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required comfort mode path: ${path}" >&2
        exit 1
    }
done

grep -q 'Apply Comfort Mode' "${SECURITY_PANEL}" || {
    echo "security panel does not expose the comfort mode quick action." >&2
    exit 1
}

grep -q 'Comfort Mode quickly switches to the Relaxed baseline while keeping your existing overrides.' "${SECURITY_PANEL}" || {
    echo "security panel does not explain comfort mode behavior." >&2
    exit 1
}

grep -q 'def on_apply_comfort_mode' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define the comfort mode apply handler." >&2
    exit 1
}

grep -q 'self.client.apply_preset("relaxed")' "${CONTROL_CENTER_MAIN}" || {
    echo "comfort mode handler does not switch to relaxed profile." >&2
    exit 1
}

grep -q 'self.client.set_overrides(current_overrides)' "${CONTROL_CENTER_MAIN}" || {
    echo "comfort mode handler does not preserve existing overrides." >&2
    exit 1
}

grep -q 'snapshot_current_settings(reason="Before comfort mode")' "${CONTROL_CENTER_MAIN}" || {
    echo "comfort mode handler does not capture a rollback snapshot." >&2
    exit 1
}

echo "Comfort mode checks passed."
