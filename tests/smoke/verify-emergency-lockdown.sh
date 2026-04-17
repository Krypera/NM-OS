#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SYSTEM_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/system.py"

for path in "${CONTROL_CENTER_MAIN}" "${SYSTEM_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required emergency lockdown path: ${path}" >&2
        exit 1
    }
done

grep -q 'Emergency Lockdown' "${SYSTEM_PANEL}" || {
    echo "system panel does not expose the Emergency Lockdown action." >&2
    exit 1
}

grep -q 'def on_emergency_lockdown' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define emergency lockdown handler." >&2
    exit 1
}

grep -q 'self._set_dropdown_value(self.network_combo, \[value for value, _label in self.NETWORK_OPTIONS\], "offline")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not force offline network policy." >&2
    exit 1
}

grep -q 'self._set_dropdown_value(self.logging_combo, \[value for value, _label in self.LOGGING_OPTIONS\], "sealed")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not force sealed logging policy." >&2
    exit 1
}

grep -q 'self._set_dropdown_value(self.device_policy_combo, \[value for value, _label in self.DEVICE_POLICY_OPTIONS\], "locked")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not force locked device policy." >&2
    exit 1
}

grep -q 'self._set_dropdown_value(self.sandbox_combo, \[value for value, _label in self.SANDBOX_OPTIONS\], "strict")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not force strict sandbox default." >&2
    exit 1
}

grep -q 'self._set_dropdown_value(self.ram_wipe_combo, \[value for value, _label in self.RAM_WIPE_OPTIONS\], "strict")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not force strict RAM wipe mode." >&2
    exit 1
}

grep -q 'self.vault_unlock_on_login.set_active(False)' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not disable vault unlock-on-login." >&2
    exit 1
}

grep -q 'self.set_all_app_overrides(filesystem="none", network="isolated", devices="none")' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not tighten per-app overrides." >&2
    exit 1
}

grep -q 'locked_now = self.try_lock_vault_now()' "${CONTROL_CENTER_MAIN}" || {
    echo "emergency lockdown does not attempt an immediate vault lock." >&2
    exit 1
}

echo "Emergency lockdown checks passed."
