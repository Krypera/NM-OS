#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETTINGS_SERVICE="${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-settings.service"
PERSISTENT_SERVICE="${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-persistent-storage.service"
NETWORK_SERVICE="${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-network-bootstrap.service"

for unit in "${SETTINGS_SERVICE}" "${PERSISTENT_SERVICE}" "${NETWORK_SERVICE}"; do
    [ -f "${unit}" ] || {
        echo "missing systemd unit: ${unit}" >&2
        exit 1
    }
    grep -q '^NoNewPrivileges=yes$' "${unit}" || {
        echo "service hardening missing NoNewPrivileges: ${unit}" >&2
        exit 1
    }
    grep -q '^ProtectSystem=strict$' "${unit}" || {
        echo "service hardening missing ProtectSystem=strict: ${unit}" >&2
        exit 1
    }
    grep -q '^ProtectHome=yes$' "${unit}" || {
        echo "service hardening missing ProtectHome=yes: ${unit}" >&2
        exit 1
    }
    grep -q '^PrivateTmp=yes$' "${unit}" || {
        echo "service hardening missing PrivateTmp=yes: ${unit}" >&2
        exit 1
    }
    grep -q '^CapabilityBoundingSet=' "${unit}" || {
        echo "service hardening missing CapabilityBoundingSet: ${unit}" >&2
        exit 1
    }
done

grep -q '^ReadWritePaths=@NMOS_RUNTIME_DIR@ @NMOS_STATE_DIR@$' "${SETTINGS_SERVICE}" || {
    echo "settings service hardening is not platform-adapter aware for write paths." >&2
    exit 1
}

grep -q '^RestrictAddressFamilies=AF_UNIX$' "${SETTINGS_SERVICE}" || {
    echo "settings service hardening is missing AF_UNIX restriction." >&2
    exit 1
}

grep -q '^ReadWritePaths=@NMOS_RUNTIME_DIR@ @NMOS_STATE_DIR@$' "${PERSISTENT_SERVICE}" || {
    echo "persistent storage service hardening is not platform-adapter aware for write paths." >&2
    exit 1
}

grep -q '^ReadWritePaths=@NMOS_RUNTIME_DIR@$' "${NETWORK_SERVICE}" || {
    echo "network bootstrap service hardening is not platform-adapter aware for write path." >&2
    exit 1
}

grep -q '^RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK$' "${NETWORK_SERVICE}" || {
    echo "network bootstrap service hardening is missing address family restrictions." >&2
    exit 1
}

echo "Systemd service hardening checks passed."
