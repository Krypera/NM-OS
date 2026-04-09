#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
STEM="nmos-amd64-${VERSION}"
IMG_PATH="${ROOT_DIR}/dist/${STEM}.img"
ISO_PATH="${ROOT_DIR}/dist/${STEM}.iso"
CHECKSUM_PATH="${ROOT_DIR}/dist/${STEM}.sha256"
PACKAGES_PATH="${ROOT_DIR}/dist/${STEM}.packages"
MANIFEST_PATH="${ROOT_DIR}/dist/${STEM}.build-manifest"

for path in "${IMG_PATH}" "${ISO_PATH}" "${CHECKSUM_PATH}" "${PACKAGES_PATH}" "${MANIFEST_PATH}"; do
    [ -s "${path}" ] || {
        echo "missing or empty artifact: ${path}" >&2
        exit 1
    }
done

command -v fdisk >/dev/null 2>&1 || {
    echo "missing required command: fdisk" >&2
    exit 1
}
command -v xorriso >/dev/null 2>&1 || {
    echo "missing required command: xorriso" >&2
    exit 1
}

fdisk -l "${IMG_PATH}" >/dev/null
xorriso -indev "${ISO_PATH}" -toc >/dev/null 2>&1
sha256sum -c "${CHECKSUM_PATH}" >/dev/null

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
GRUB_CFG="${TMP_DIR}/grub.cfg"
SYSLINUX_CFG="${TMP_DIR}/live.cfg"

xorriso -osirrox on -indev "${ISO_PATH}" -extract /boot/grub/grub.cfg "${GRUB_CFG}" >/dev/null 2>&1 || {
    echo "unable to extract /boot/grub/grub.cfg from ISO." >&2
    exit 1
}

if ! xorriso -osirrox on -indev "${ISO_PATH}" -extract /isolinux/live.cfg "${SYSLINUX_CFG}" >/dev/null 2>&1; then
    xorriso -osirrox on -indev "${ISO_PATH}" -extract /syslinux/live.cfg "${SYSLINUX_CFG}" >/dev/null 2>&1 || {
        echo "unable to extract BIOS live.cfg from ISO." >&2
        exit 1
    }
fi

for entry in "NM-OS (Strict)" "NM-OS (Flexible)" "NM-OS (Offline)" "NM-OS (Recovery)" "NM-OS (Hardware Compatibility)"; do
    grep -q "${entry}" "${GRUB_CFG}" || {
        echo "grub menu is missing entry: ${entry}" >&2
        exit 1
    }
    grep -q "${entry}" "${SYSLINUX_CFG}" || {
        echo "syslinux menu is missing entry: ${entry}" >&2
        exit 1
    }
done

grep -q "nmos.mode=compat nomodeset" "${GRUB_CFG}" || {
    echo "grub compatibility entry is missing nmos.mode=compat nomodeset." >&2
    exit 1
}
grep -q "nmos.mode=compat nomodeset" "${SYSLINUX_CFG}" || {
    echo "syslinux compatibility entry is missing nmos.mode=compat nomodeset." >&2
    exit 1
}

grep -q "^img=${STEM}\.img$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the img artifact." >&2
    exit 1
}
grep -q "^iso=${STEM}\.iso$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the iso artifact." >&2
    exit 1
}

echo "Artifacts look consistent."
