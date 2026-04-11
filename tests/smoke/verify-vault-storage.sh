#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STORAGE_FILE="${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/storage.py"
OPS_FILE="${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/mount_crypto_ops.py"
TMPFILES_FILE="${ROOT_DIR}/config/system-overlay/usr/lib/tmpfiles.d/nmos.conf"
SERVICE_FILE="${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-persistent-storage.service"

grep -q 'VAULT_IMAGE_PATH = STORAGE_ROOT / "vault.img"' "${STORAGE_FILE}" || {
    echo "persistent storage backend does not use a file-based encrypted vault." >&2
    exit 1
}

grep -q 'DEFAULT_VAULT_SIZE_BYTES' "${STORAGE_FILE}" || {
    echo "persistent storage backend does not define a default vault size." >&2
    exit 1
}

grep -q 'create_image_file' "${OPS_FILE}" || {
    echo "crypto operations layer does not create the vault image file." >&2
    exit 1
}

grep -q '@NMOS_STATE_DIR@/storage' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the vault storage directory via platform adapter path." >&2
    exit 1
}

grep -q '^ReadWritePaths=@NMOS_RUNTIME_DIR@ @NMOS_STATE_DIR@$' "${SERVICE_FILE}" || {
    echo "persistent storage service is missing platform-adapter-aware write paths." >&2
    exit 1
}

if grep -q '/run/live/medium' "${STORAGE_FILE}"; then
    echo "persistent storage backend still depends on live boot media." >&2
    exit 1
fi

if grep -q '/live/persistence' "${STORAGE_FILE}"; then
    echo "persistent storage backend still mounts under live persistence paths." >&2
    exit 1
fi

echo "Encrypted vault storage looks configured."
