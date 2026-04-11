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
INSTALLER_ISO_STEM="nmos-installer-${VERSION}-amd64"
INSTALLER_ISO_PATH="${ROOT_DIR}/dist/${INSTALLER_ISO_STEM}.iso"
INSTALLER_ISO_CHECKSUM_PATH="${ROOT_DIR}/dist/${INSTALLER_ISO_STEM}.sha256"

for path in \
    "${ARCHIVE_PATH}" \
    "${CHECKSUM_PATH}" \
    "${PACKAGES_PATH}" \
    "${MANIFEST_PATH}" \
    "${INSTALLER_ARCHIVE_PATH}" \
    "${INSTALLER_CHECKSUM_PATH}" \
    "${INSTALLER_PACKAGES_PATH}" \
    "${INSTALLER_ISO_PATH}" \
    "${INSTALLER_ISO_CHECKSUM_PATH}"; do
    [ -s "${path}" ] || {
        echo "missing or empty artifact: ${path}" >&2
        exit 1
    }
done

command -v tar >/dev/null 2>&1 || {
    echo "missing required command: tar" >&2
    exit 1
}
command -v xorriso >/dev/null 2>&1 || {
    echo "missing required command: xorriso" >&2
    exit 1
}

sha256sum -c "${CHECKSUM_PATH}" >/dev/null
sha256sum -c "${INSTALLER_CHECKSUM_PATH}" >/dev/null
sha256sum -c "${INSTALLER_ISO_CHECKSUM_PATH}" >/dev/null

TMP_DIR="$(mktemp -d)"
INSTALLER_TMP_DIR="$(mktemp -d)"
ISO_TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}" "${INSTALLER_TMP_DIR}" "${ISO_TMP_DIR}"' EXIT

tar -xzf "${ARCHIVE_PATH}" -C "${TMP_DIR}"
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
    "${INSTALLER_TMP_DIR}/debian-installer/preseed/nmos.cfg.in" \
    "${INSTALLER_TMP_DIR}/debian-installer/preseed/install-overlay.sh.in" \
    "${INSTALLER_TMP_DIR}/packages/base.txt"; do
    [ -f "${path}" ] || {
        echo "installer assets archive is missing expected file: ${path}" >&2
        exit 1
    }
done

xorriso -osirrox on -indev "${INSTALLER_ISO_PATH}" \
    -extract /preseed/nmos.cfg "${ISO_TMP_DIR}/nmos.cfg" \
    -extract /isolinux/txt.cfg "${ISO_TMP_DIR}/txt.cfg" \
    -extract /boot/grub/grub.cfg "${ISO_TMP_DIR}/grub.cfg" \
    -extract "/nmos/${STEM}.tar.gz" "${ISO_TMP_DIR}/overlay.tar.gz" \
    -extract "/nmos/${STEM}.packages" "${ISO_TMP_DIR}/packages.txt" \
    -extract /md5sum.txt "${ISO_TMP_DIR}/md5sum.txt" >/dev/null 2>&1

cmp -s "${ISO_TMP_DIR}/overlay.tar.gz" "${ARCHIVE_PATH}" || {
    echo "installer ISO does not embed the built overlay archive." >&2
    exit 1
}

cmp -s "${ISO_TMP_DIR}/packages.txt" "${PACKAGES_PATH}" || {
    echo "installer ISO does not embed the runtime package manifest." >&2
    exit 1
}

grep -q 'pkgsel/include string' "${ISO_TMP_DIR}/nmos.cfg" || {
    echo "installer ISO preseed does not install the runtime package set." >&2
    exit 1
}

grep -q 'preseed/file=/cdrom/preseed/nmos.cfg' "${ISO_TMP_DIR}/txt.cfg" || {
    echo "installer ISO BIOS menu does not point at the NM-OS preseed file." >&2
    exit 1
}

grep -q 'Install NM-OS' "${ISO_TMP_DIR}/grub.cfg" || {
    echo "installer ISO UEFI menu does not expose the NM-OS entry." >&2
    exit 1
}

grep -q './preseed/nmos.cfg' "${ISO_TMP_DIR}/md5sum.txt" || {
    echo "installer ISO checksum manifest does not cover the NM-OS preseed file." >&2
    exit 1
}

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
grep -q "^installer_iso=${INSTALLER_ISO_STEM}\.iso$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the installer ISO." >&2
    exit 1
}
grep -q "^installer_stack=debian-installer$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the Debian installer stack." >&2
    exit 1
}
grep -q "^installer_ui=calamares-assets$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the installer UI scaffolding." >&2
    exit 1
}
grep -q "^app_isolation=flatpak-portals$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the app isolation stack." >&2
    exit 1
}

echo "Artifacts look consistent."
