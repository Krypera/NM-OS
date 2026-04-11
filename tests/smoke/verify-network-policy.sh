#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_FILE="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/network_bootstrap.py"
STATUS_FILE="${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/tor_bootstrap_status.py"

grep -q 'load_system_settings' "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not read persisted system settings." >&2
    exit 1
}

grep -q 'policy == "offline"' "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not handle offline policy." >&2
    exit 1
}

grep -q 'policy == "direct"' "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not handle direct policy." >&2
    exit 1
}

grep -q 'write_tor_firewall_rules' "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not keep a Tor-first firewall flow." >&2
    exit 1
}

if grep -q 'load_boot_mode_profile' "${BOOTSTRAP_FILE}"; then
    echo "network bootstrap still reads boot mode state." >&2
    exit 1
fi

grep -q 'policy == "offline"' "${STATUS_FILE}" || {
    echo "Tor status helper does not reflect offline policy." >&2
    exit 1
}

grep -q 'policy == "direct"' "${STATUS_FILE}" || {
    echo "Tor status helper does not reflect direct policy." >&2
    exit 1
}

echo "Network policy wiring looks configured."
