#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"

[ -f "${CONTROL_CENTER_MAIN}" ] || {
    echo "missing control center source: ${CONTROL_CENTER_MAIN}" >&2
    exit 1
}

grep -q 'SETTING_RISK_HINTS = {' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define SETTING_RISK_HINTS." >&2
    exit 1
}

for key in \
    'network_policy' \
    'allow_brave_browser' \
    'sandbox_default' \
    'default_browser' \
    'device_policy' \
    'logging_policy' \
    'ram_wipe_mode' \
    'vault_auto_lock_minutes' \
    'vault_unlock_on_login' \
    'app_overrides' \
    'active_profile'; do
    grep -q "\"${key}\":" "${CONTROL_CENTER_MAIN}" || {
        echo "missing security risk hint key: ${key}" >&2
        exit 1
    }
    grep -q "build_setting_change_explanation(key=\"${key}\"" "${CONTROL_CENTER_MAIN}" || {
        echo "missing change explanation wiring for key: ${key}" >&2
        exit 1
    }
done

grep -q 'Explain this setting:' "${CONTROL_CENTER_MAIN}" || {
    echo "control center explanation format does not include explicit setting context." >&2
    exit 1
}

grep -q 'Changes now:' "${CONTROL_CENTER_MAIN}" || {
    echo "control center explanation format does not include immediate impact flag." >&2
    exit 1
}

grep -q 'Changes after reboot:' "${CONTROL_CENTER_MAIN}" || {
    echo "control center explanation format does not include reboot impact flag." >&2
    exit 1
}

grep -q 'Compatibility risk:' "${CONTROL_CENTER_MAIN}" || {
    echo "control center explanation format does not include compatibility risk." >&2
    exit 1
}

echo "Security setting explanation checks passed."
