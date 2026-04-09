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

grep -q "^img=${STEM}\.img$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the img artifact." >&2
    exit 1
}
grep -q "^iso=${STEM}\.iso$" "${MANIFEST_PATH}" || {
    echo "build manifest does not record the iso artifact." >&2
    exit 1
}

echo "Artifacts look consistent."

