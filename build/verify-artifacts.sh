#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
STEM="nmos-system-overlay-${VERSION}"
ARCHIVE_PATH="${ROOT_DIR}/dist/${STEM}.tar.gz"
CHECKSUM_PATH="${ROOT_DIR}/dist/${STEM}.sha256"
PACKAGES_PATH="${ROOT_DIR}/dist/${STEM}.packages"
MANIFEST_PATH="${ROOT_DIR}/dist/${STEM}.build-manifest"
INSTALLER_STEM="nmos-installer-assets-${VERSION}"
INSTALLER_ARCHIVE_PATH="${ROOT_DIR}/dist/${INSTALLER_STEM}.tar.gz"
INSTALLER_CHECKSUM_PATH="${ROOT_DIR}/dist/${INSTALLER_STEM}.sha256"
INSTALLER_PACKAGES_PATH="${ROOT_DIR}/dist/${INSTALLER_STEM}.packages"

for path in "${ARCHIVE_PATH}" "${CHECKSUM_PATH}" "${PACKAGES_PATH}" "${MANIFEST_PATH}" "${INSTALLER_ARCHIVE_PATH}" "${INSTALLER_CHECKSUM_PATH}" "${INSTALLER_PACKAGES_PATH}"; do
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
sha256sum -c "${INSTALLER_CHECKSUM_PATH}" >/dev/null

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"

INSTALLER_TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}" "${INSTALLER_TMP_DIR}"' EXIT
tar -xzf "${INSTALLER_ARCHIVE_PATH}" -C "${INSTALLER_TMP_DIR}"

for path in \
    "${TMP_DIR}/etc/dbus-1/system.d/org.nmos.Settings1.conf" \
    "${TMP_DIR}/usr/local/lib/nmos/settings_bootstrap.py" \
    "${TMP_DIR}/usr/local/lib/nmos/network_bootstrap.py" \
    "${TMP_DIR}/usr/local/lib/nmos/brave_policy.py" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-settings.service" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-settings-bootstrap.service" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-network-bootstrap.service" \
    "${TMP_DIR}/usr/lib/systemd/system/nmos-persistent-storage.service" \
    "${TMP_DIR}/usr/share/applications/nmos-control-center.desktop" \
    "${TMP_DIR}/usr/share/nmos/theme/nmos.css" \
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

for path in \
    "${INSTALLER_TMP_DIR}/calamares/settings.conf" \
    "${INSTALLER_TMP_DIR}/calamares/branding/nmos/branding.desc" \
    "${INSTALLER_TMP_DIR}/packages/base.txt"; do
    [ -f "${path}" ] || {
        echo "installer assets archive is missing expected file: ${path}" >&2
        exit 1
    }
done

grep -q "^artifact=${STEM}\.tar\.gz$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the overlay artifact." >&2
    exit 1
}
grep -q "^artifact_type=system-overlay$" "${MANIFEST_PATH}" || {
    echo "build manifest does not describe the system overlay artifact type." >&2
    exit 1
}
grep -q "^installer_assets=${INSTALLER_STEM}\.tar\.gz$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the installer assets archive." >&2
    exit 1
}
grep -q "^installer_stack=calamares$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the installer stack." >&2
    exit 1
}
grep -q "^app_isolation=flatpak-portals$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the app isolation stack." >&2
    exit 1
}

echo "Artifacts look consistent."
