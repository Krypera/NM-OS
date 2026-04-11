#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
STEM="nmos-system-overlay-${VERSION}"
ARCHIVE_PATH="${ROOT_DIR}/dist/${STEM}.tar.gz"
CHECKSUM_PATH="${ROOT_DIR}/dist/${STEM}.sha256"
PACKAGES_PATH="${ROOT_DIR}/dist/${STEM}.packages"
MANIFEST_PATH="${ROOT_DIR}/dist/${STEM}.build-manifest"

for path in "${ARCHIVE_PATH}" "${CHECKSUM_PATH}" "${PACKAGES_PATH}" "${MANIFEST_PATH}"; do
    [ -s "${path}" ] || {
        echo "missing or empty artifact: ${path}" >&2
        exit 1
    }
done

command -v tar >/dev/null 2>&1 || {
    echo "missing required command: tar" >&2
    exit 1
}

sha256sum -c "${CHECKSUM_PATH}" >/dev/null

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"

for path in \
    "${TMP_DIR}/usr/local/lib/nmos/settings_bootstrap.py" \
    "${TMP_DIR}/usr/local/lib/nmos/network_bootstrap.py" \
    "${TMP_DIR}/usr/local/lib/nmos/brave_policy.py" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-settings-bootstrap.service" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-network-bootstrap.service" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-persistent-storage.service" \
    "${TMP_DIR}/usr/share/gdm/greeter/applications/nmos-greeter.desktop" \
    "${TMP_DIR}/etc/gdm3/PostLogin/Default"; do
    [ -f "${path}" ] || {
        echo "overlay archive is missing expected file: ${path}" >&2
        exit 1
    }
done

if [ -e "${TMP_DIR}/usr/lib/systemd/system/nmos-live-user-password.service" ]; then
    echo "overlay archive still contains legacy password wiring." >&2
    exit 1
fi

if [ -e "${TMP_DIR}/usr/local/lib/nmos/ensure_live_user_password.py" ]; then
    echo "overlay archive still contains legacy password helper." >&2
    exit 1
fi

grep -q "^artifact=${STEM}\.tar\.gz$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the overlay artifact." >&2
    exit 1
}
grep -q "^artifact_type=system-overlay$" "${MANIFEST_PATH}" || {
    echo "build manifest does not describe the system overlay artifact type." >&2
    exit 1
}

echo "Artifacts look consistent."
