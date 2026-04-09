#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/network_bootstrap.py"

grep -q "def write_firewall_rules" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not define the pre-login firewall gate." >&2
    exit 1
}

grep -q "def write_offline_firewall_rules" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not define the offline fail-closed firewall gate." >&2
    exit 1
}

grep -q "def remove_firewall_gate" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not define firewall gate removal after Tor readiness." >&2
    exit 1
}

grep -q "def nft_table_exists" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not verify whether the temporary nftables table still exists." >&2
    exit 1
}

grep -q "remove_firewall_gate()" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap never removes the temporary firewall gate." >&2
    exit 1
}

grep -q "load_boot_mode_profile" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not read the runtime boot mode profile." >&2
    exit 1
}

grep -q "MODE_OFFLINE" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not branch on offline mode." >&2
    exit 1
}

grep -q "MODE_RECOVERY" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not branch on recovery mode." >&2
    exit 1
}

grep -q "phase=\"disabled\"" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not emit a disabled status phase for offline modes." >&2
    exit 1
}

echo "Network gate transition wiring looks configured."
