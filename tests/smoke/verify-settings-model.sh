#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETTINGS_MODULE="${ROOT_DIR}/apps/nmos_common/nmos_common/system_settings.py"
SETTINGS_BOOTSTRAP="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/settings_bootstrap.py"
MAIN_FILE="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"

for path in "${SETTINGS_MODULE}" "${SETTINGS_BOOTSTRAP}" "${MAIN_FILE}"; do
    [ -f "${path}" ] || {
        echo "missing settings model path: ${path}" >&2
        exit 1
    }
done

grep -q 'PERSISTENT_SETTINGS_FILE = Path("/var/lib/nmos/system-settings.json")' "${SETTINGS_MODULE}" || {
    echo "system settings module does not use the persistent settings file." >&2
    exit 1
}

grep -q 'RUNTIME_SETTINGS_FILE = Path("/run/nmos/system-settings.json")' "${SETTINGS_MODULE}" || {
    echo "system settings module does not use the runtime settings file." >&2
    exit 1
}

grep -q 'SUPPORTED_NETWORK_POLICIES = {"tor", "direct", "offline"}' "${SETTINGS_MODULE}" || {
    echo "system settings module does not expose the expected network policies." >&2
    exit 1
}

grep -q 'save_system_settings' "${MAIN_FILE}" || {
    echo "setup assistant does not persist system settings." >&2
    exit 1
}

if grep -q 'boot_mode' "${MAIN_FILE}"; then
    echo "setup assistant still references boot modes." >&2
    exit 1
fi

echo "System settings model looks configured."
