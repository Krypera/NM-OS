#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"

[ -f "${CONTROL_CENTER_MAIN}" ] || {
    echo "missing control center source: ${CONTROL_CENTER_MAIN}" >&2
    exit 1
}

grep -q 'def _set_review_mode_status' "${CONTROL_CENTER_MAIN}" || {
    echo "review mode helper is missing." >&2
    exit 1
}

grep -q 'Review mode only until service is reachable. Use Diagnostics for details.' "${CONTROL_CENTER_MAIN}" || {
    echo "review mode helper does not include expected guidance text." >&2
    exit 1
}

for callsite in \
    'self._set_review_mode_status(self.startup_error_message)' \
    'self._set_review_mode_status(self.format_backend_guidance(error))' \
    'self._set_review_mode_status("Settings backend is unavailable.")'; do
    grep -q "${callsite}" "${CONTROL_CENTER_MAIN}" || {
        echo "review mode helper callsite is missing: ${callsite}" >&2
        exit 1
    }
done

if grep -q 'Review mode only until service is reachable\.$' "${CONTROL_CENTER_MAIN}"; then
    echo "legacy short review mode text detected; use unified helper guidance." >&2
    exit 1
fi

echo "Review mode messaging checks passed."
