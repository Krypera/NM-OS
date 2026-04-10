#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/network_bootstrap.py"
BOOTSTRAP_SERVICE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-network-bootstrap.service"

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

grep -q "ensure_online_bootstrap_services" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not conditionally start online-mode dependencies." >&2
    exit 1
}

grep -q '^After=nmos-boot-profile.service$' "${BOOTSTRAP_SERVICE}" || {
    echo "network bootstrap service is not anchored to boot-profile ordering." >&2
    exit 1
}

if grep -Eq '(^|[[:space:]])tor(@default)?\.service' "${BOOTSTRAP_SERVICE}"; then
    echo "network bootstrap service still hard-depends on tor services for every boot mode." >&2
    exit 1
fi

if grep -Eq '(^|[[:space:]])NetworkManager\.service' "${BOOTSTRAP_SERVICE}"; then
    echo "network bootstrap service still hard-depends on NetworkManager for every boot mode." >&2
    exit 1
fi

echo "Network gate transition wiring looks configured."
