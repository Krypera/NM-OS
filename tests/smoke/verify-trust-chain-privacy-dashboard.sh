#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SYSTEM_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/system.py"

for path in "${CONTROL_CENTER_MAIN}" "${SYSTEM_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required trust/privacy path: ${path}" >&2
        exit 1
    }
done

grep -q 'Privacy dashboard' "${SYSTEM_PANEL}" || {
    echo "system panel does not expose Privacy dashboard section." >&2
    exit 1
}

grep -q 'Trust chain viewer' "${SYSTEM_PANEL}" || {
    echo "system panel does not expose Trust chain viewer section." >&2
    exit 1
}

grep -q 'def format_privacy_dashboard' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define privacy dashboard formatter." >&2
    exit 1
}

grep -q 'Active policies:' "${CONTROL_CENTER_MAIN}" || {
    echo "privacy dashboard does not include active policy summary." >&2
    exit 1
}

grep -q 'Recent draft changes:' "${CONTROL_CENTER_MAIN}" || {
    echo "privacy dashboard does not include recent draft changes." >&2
    exit 1
}

grep -q 'def format_trust_chain_status' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not define trust chain formatter." >&2
    exit 1
}

for required in \
    'Installed version:' \
    'Channel:' \
    'Build id:' \
    'Signatures:' \
    'Verification status:'; do
    grep -q "${required}" "${CONTROL_CENTER_MAIN}" || {
        echo "trust chain status missing required field: ${required}" >&2
        exit 1
    }
done

grep -q 'def on_refresh_trust_chain' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not provide trust-chain refresh action." >&2
    exit 1
}

echo "Trust chain and privacy dashboard checks passed."
