#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
IMAGE_PATH="${1:-${ROOT_DIR}/dist/nmos-amd64-${VERSION}.img}"
LOG_FILE="${ROOT_DIR}/dist/qemu-smoke.log"
QEMU_TIMEOUT_SECONDS="${NMOS_QEMU_TIMEOUT_SECONDS:-420}"
EXPECT_NETWORK_MARKER="${NMOS_QEMU_EXPECT_NETWORK_MARKER:-1}"
NETWORK_MARKER="${NMOS_QEMU_NETWORK_MARKER:-NMOS_NETWORK_READY}"

if [ ! -f "${IMAGE_PATH}" ]; then
    echo "Image not found: ${IMAGE_PATH}" >&2
    exit 1
fi

command -v qemu-system-x86_64 >/dev/null 2>&1 || {
    echo "missing required command: qemu-system-x86_64" >&2
    exit 1
}

QEMU_ACCEL=()
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    QEMU_ACCEL=(-enable-kvm)
fi

if [[ "${IMAGE_PATH}" == *.iso ]]; then
    timeout "${QEMU_TIMEOUT_SECONDS}" qemu-system-x86_64 \
        -m 4096 \
        -smp 2 \
        -cdrom "${IMAGE_PATH}" \
        -nic user,model=virtio-net-pci \
        -boot d \
        -display none \
        -serial stdio \
        -no-reboot \
        "${QEMU_ACCEL[@]}" \
        2>&1 | tee "${LOG_FILE}"
else
    timeout "${QEMU_TIMEOUT_SECONDS}" qemu-system-x86_64 \
        -m 4096 \
        -smp 2 \
        -drive file="${IMAGE_PATH}",format=raw,if=virtio \
        -nic user,model=virtio-net-pci \
        -display none \
        -serial stdio \
        -no-reboot \
        "${QEMU_ACCEL[@]}" \
        2>&1 | tee "${LOG_FILE}"
fi

grep -q "NMOS_BOOT_OK" "${LOG_FILE}" || {
    echo "boot marker was not observed in QEMU output." >&2
    exit 1
}

grep -q "NMOS_BOOT_MODE" "${LOG_FILE}" || {
    echo "boot mode marker was not observed in QEMU output." >&2
    exit 1
}

if [ "${EXPECT_NETWORK_MARKER}" = "1" ]; then
    grep -q "${NETWORK_MARKER}" "${LOG_FILE}" || {
        echo "expected network marker was not observed in QEMU output: ${NETWORK_MARKER}" >&2
        exit 1
    }
fi

echo "QEMU smoke check passed."
