#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
WORK_DIR="${ROOT_DIR}/.build/live-build"
DIST_DIR="${ROOT_DIR}/dist"
LIVE_BUILD_SOURCE="${ROOT_DIR}/config/live-build"
HOOKS_SOURCE="${ROOT_DIR}/hooks/live"
APPS_SOURCE="${ROOT_DIR}/apps"

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing required command: $1" >&2
        exit 1
    }
}

prepare_directories() {
    mkdir -p "${WORK_DIR}" "${DIST_DIR}"
}

stage_live_build_tree() {
    prepare_directories
    rm -rf "${WORK_DIR}"
    mkdir -p "${WORK_DIR}"
    rsync -a --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.pyo' "${LIVE_BUILD_SOURCE}/" "${WORK_DIR}/"
    mkdir -p "${WORK_DIR}/config/hooks/live"
    rsync -a --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.pyo' "${HOOKS_SOURCE}/" "${WORK_DIR}/config/hooks/live/"
    mkdir -p "${WORK_DIR}/config/includes.chroot/usr/src/nmos/apps"
    rsync -a --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.pyo' "${APPS_SOURCE}/" "${WORK_DIR}/config/includes.chroot/usr/src/nmos/apps/"
    mkdir -p "${WORK_DIR}/config/includes.chroot/usr/share/nmos"
    cat > "${WORK_DIR}/config/includes.chroot/usr/share/nmos/build-info" <<EOF
NMOS_VERSION=${VERSION}
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
    if find "${WORK_DIR}" \( -type d -name "__pycache__" -o -type f \( -name "*.pyc" -o -name "*.pyo" \) \) | grep -q .; then
        echo "staged live-build tree contains Python cache artifacts." >&2
        exit 1
    fi
    chmod +x "${WORK_DIR}/auto/config" "${WORK_DIR}/auto/build"
    find "${WORK_DIR}/config/hooks/live" -type f -name "*.hook.chroot" -exec chmod +x {} +
    if [ -d "${WORK_DIR}/config/includes.chroot/usr/local/bin" ]; then
        find "${WORK_DIR}/config/includes.chroot/usr/local/bin" -type f -exec chmod +x {} +
    fi
    if [ -d "${WORK_DIR}/config/includes.chroot/usr/local/lib/nmos" ]; then
        find "${WORK_DIR}/config/includes.chroot/usr/local/lib/nmos" -type f -name "*.py" -exec chmod +x {} +
    fi
    if [ -d "${WORK_DIR}/config/includes.chroot/etc/gdm3/PostLogin" ]; then
        find "${WORK_DIR}/config/includes.chroot/etc/gdm3/PostLogin" -type f -exec chmod +x {} +
    fi
}

find_built_iso() {
    find "${WORK_DIR}" -maxdepth 1 -type f -name "*.iso" | head -n 1
}

build_output_stem() {
    echo "nmos-amd64-${VERSION}"
}

build_iso_name() {
    echo "$(build_output_stem).iso"
}

build_img_name() {
    echo "$(build_output_stem).img"
}
