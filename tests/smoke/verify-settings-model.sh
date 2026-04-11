#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETTINGS_MODULE="${ROOT_DIR}/apps/nmos_common/nmos_common/system_settings.py"
SETTINGS_CLIENT="${ROOT_DIR}/apps/nmos_common/nmos_common/settings_client.py"
SETTINGS_SERVICE="${ROOT_DIR}/apps/nmos_settings/nmos_settings/service.py"
SETTINGS_BOOTSTRAP="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/settings_bootstrap.py"
MAIN_FILE="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"

for path in "${SETTINGS_MODULE}" "${SETTINGS_CLIENT}" "${SETTINGS_SERVICE}" "${SETTINGS_BOOTSTRAP}" "${MAIN_FILE}"; do
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

grep -q 'SCHEMA_VERSION = 1' "${SETTINGS_MODULE}" || {
    echo "system settings module does not declare the schema version." >&2
    exit 1
}

grep -q 'SUPPORTED_SECURITY_PROFILES = ("relaxed", "balanced", "hardened", "maximum")' "${SETTINGS_MODULE}" || {
    echo "system settings module does not expose the expected security profiles." >&2
    exit 1
}

grep -q 'SUPPORTED_NETWORK_POLICIES = {"tor", "direct", "offline"}' "${SETTINGS_MODULE}" || {
    echo "system settings module does not expose the expected network policies." >&2
    exit 1
}

grep -q 'derive_overrides_for_profile' "${MAIN_FILE}" || {
    echo "setup assistant does not derive overrides from the selected profile." >&2
    exit 1
}

if grep -q 'boot_mode' "${MAIN_FILE}"; then
    echo "setup assistant still references boot modes." >&2
    exit 1
fi

grep -q 'org.nmos.Settings1' "${SETTINGS_CLIENT}" || {
    echo "settings client does not target org.nmos.Settings1." >&2
    exit 1
}

grep -q 'ApplyPreset' "${SETTINGS_SERVICE}" || {
    echo "settings service does not expose ApplyPreset." >&2
    exit 1
}

grep -q 'GetPendingRebootChanges' "${SETTINGS_SERVICE}" || {
    echo "settings service does not expose GetPendingRebootChanges." >&2
    exit 1
}

echo "System settings model looks configured."
