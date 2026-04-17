#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"

[ -f "${CONTROL_CENTER_MAIN}" ] || {
    echo "missing control center source: ${CONTROL_CENTER_MAIN}" >&2
    exit 1
}

grep -q 'def _set_backend_action_sensitivity' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define backend action sensitivity helper." >&2
    exit 1
}

grep -q 'def _guard_backend_mutation' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define backend mutation guard helper." >&2
    exit 1
}

for button in \
    'self.apply_button.set_sensitive(enabled)' \
    'self.reset_button.set_sensitive(enabled)' \
    'self.comfort_mode_button.set_sensitive(enabled)' \
    'self.emergency_lockdown_button.set_sensitive(enabled)'; do
    grep -q "${button}" "${CONTROL_CENTER_MAIN}" || {
        echo "backend action helper is missing button sensitivity control: ${button}" >&2
        exit 1
    }
done

grep -q 'self._set_backend_action_sensitivity(self.backend_ready)' "${CONTROL_CENTER_MAIN}" || {
    echo "initial backend action sensitivity setup is missing." >&2
    exit 1
}

grep -q 'self._set_backend_action_sensitivity(True)' "${CONTROL_CENTER_MAIN}" || {
    echo "backend recovery path does not re-enable mutation controls." >&2
    exit 1
}

grep -q 'self._set_backend_action_sensitivity(False)' "${CONTROL_CENTER_MAIN}" || {
    echo "backend failure path does not disable mutation controls." >&2
    exit 1
}

for callsite in \
    'if not self._guard_backend_mutation():' \
    'Settings backend is unavailable. Review mode only until service is reachable.'; do
    grep -q "${callsite}" "${CONTROL_CENTER_MAIN}" || {
        echo "backend mutation guard wiring missing: ${callsite}" >&2
        exit 1
    }
done

grep -q 'def _reload_from_backend' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define backend reload handler." >&2
    exit 1
}

grep -q 'except SettingsClientError as error:' "${CONTROL_CENTER_MAIN}" || {
    echo "backend reload failure is not classified with SettingsClientError guidance." >&2
    exit 1
}

grep -q 'self.status_label.set_text(f"{self.format_backend_guidance(error)} Review mode only until service is reachable.")' "${CONTROL_CENTER_MAIN}" || {
    echo "backend reload failure does not publish explicit review mode guidance." >&2
    exit 1
}

echo "Backend action safety checks passed."
