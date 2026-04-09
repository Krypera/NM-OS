#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/network_bootstrap.py"

grep -q "def write_firewall_rules" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not define the pre-login firewall gate." >&2
    exit 1
}

grep -q "def remove_firewall_gate" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap does not define firewall gate removal after Tor readiness." >&2
    exit 1
}

grep -q "remove_firewall_gate()" "${BOOTSTRAP_FILE}" || {
    echo "network bootstrap never removes the temporary firewall gate." >&2
    exit 1
}

echo "Network gate transition wiring looks configured."
