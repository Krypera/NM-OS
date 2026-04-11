#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(tr -d '\r\n' < "${ROOT_DIR}/config/version")"
WORK_DIR="${ROOT_DIR}/.build/system-overlay"
ROOTFS_DIR="${WORK_DIR}/rootfs"
INSTALLER_WORK_DIR="${ROOT_DIR}/.build/installer-assets"
DIST_DIR="${ROOT_DIR}/dist"
SYSTEM_OVERLAY_SOURCE="${ROOT_DIR}/config/system-overlay"
SYSTEM_PACKAGES_SOURCE="${ROOT_DIR}/config/system-packages"
INSTALLER_ASSETS_SOURCE="${ROOT_DIR}/config/installer"
INSTALLER_PACKAGES_SOURCE="${ROOT_DIR}/config/installer-packages"
APPS_SOURCE="${ROOT_DIR}/apps"
TARGET_PYTHON_DIR="${ROOTFS_DIR}/usr/lib/python3/dist-packages"
VERSION_PATTERN='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?$'

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing required command: $1" >&2
        exit 1
    }
}

validate_version_format() {
    local value="${1:-${VERSION}}"
    if [[ -z "${value}" ]]; then
        echo "config/version is empty." >&2
        exit 1
    fi
    if [[ ! "${value}" =~ ${VERSION_PATTERN} ]]; then
        echo "config/version has unsupported format: ${value}" >&2
        echo "expected format: MAJOR.MINOR.PATCH[-prerelease[.tag]]" >&2
        exit 1
    fi
}

prepare_directories() {
    mkdir -p "${ROOTFS_DIR}" "${DIST_DIR}" "${INSTALLER_WORK_DIR}"
}

install_python_package_dir() {
    local package_dir="$1"
    if [ ! -d "${package_dir}" ]; then
        echo "missing package directory: ${package_dir}" >&2
        exit 1
    fi
    cp -a "${package_dir}" "${TARGET_PYTHON_DIR}/"
}

enable_system_service() {
    local unit_name="$1"
    local wants_dir="${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
    mkdir -p "${wants_dir}"
    ln -sf "/usr/lib/systemd/system/${unit_name}" "${wants_dir}/${unit_name}"
}

stage_system_overlay_tree() {
    prepare_directories
    rm -rf "${WORK_DIR}"
    mkdir -p "${ROOTFS_DIR}"
    rsync -a --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.pyo' "${SYSTEM_OVERLAY_SOURCE}/" "${ROOTFS_DIR}/"
    mkdir -p "${TARGET_PYTHON_DIR}"
    install_python_package_dir "${APPS_SOURCE}/nmos_common/nmos_common"
    install_python_package_dir "${APPS_SOURCE}/nmos_greeter/nmos_greeter"
    install_python_package_dir "${APPS_SOURCE}/nmos_persistent_storage/nmos_persistent_storage"
    install_python_package_dir "${APPS_SOURCE}/nmos_settings/nmos_settings"
    install_python_package_dir "${APPS_SOURCE}/nmos_control_center/nmos_control_center"
    mkdir -p "${ROOTFS_DIR}/usr/share/nmos"
    cat > "${ROOTFS_DIR}/usr/share/nmos/build-info" <<EOF
NMOS_VERSION=${VERSION}
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
    enable_system_service "nmos-settings.service"
    enable_system_service "nmos-settings-bootstrap.service"
    enable_system_service "nmos-boot-marker.service"
    enable_system_service "nmos-network-bootstrap.service"
    enable_system_service "nmos-persistent-storage.service"
    if find "${WORK_DIR}" \( -type d -name "__pycache__" -o -type f \( -name "*.pyc" -o -name "*.pyo" \) \) | grep -q .; then
        echo "staged system overlay tree contains Python cache artifacts." >&2
        exit 1
    fi
    if [ -d "${ROOTFS_DIR}/usr/local/bin" ]; then
        find "${ROOTFS_DIR}/usr/local/bin" -type f -exec chmod +x {} +
    fi
    if [ -d "${ROOTFS_DIR}/usr/local/lib/nmos" ]; then
        find "${ROOTFS_DIR}/usr/local/lib/nmos" -type f -name "*.py" -exec chmod +x {} +
        find "${ROOTFS_DIR}/usr/local/lib/nmos" -type f -name "*.sh" -exec chmod +x {} +
    fi
    if [ -d "${ROOTFS_DIR}/etc/gdm3/PostLogin" ]; then
        find "${ROOTFS_DIR}/etc/gdm3/PostLogin" -type f -exec chmod +x {} +
    fi
}

stage_installer_assets_tree() {
    prepare_directories
    rm -rf "${INSTALLER_WORK_DIR}"
    mkdir -p "${INSTALLER_WORK_DIR}"
    if [ -d "${INSTALLER_ASSETS_SOURCE}" ]; then
        rsync -a --exclude '__pycache__/' "${INSTALLER_ASSETS_SOURCE}/" "${INSTALLER_WORK_DIR}/"
    fi
    if [ -d "${INSTALLER_PACKAGES_SOURCE}" ]; then
        mkdir -p "${INSTALLER_WORK_DIR}/packages"
        rsync -a "${INSTALLER_PACKAGES_SOURCE}/" "${INSTALLER_WORK_DIR}/packages/"
    fi
}

build_output_stem() {
    echo "nmos-system-overlay-${VERSION}"
}

build_archive_name() {
    echo "$(build_output_stem).tar.gz"
}

installer_output_stem() {
    echo "nmos-installer-assets-${VERSION}"
}

installer_archive_name() {
    echo "$(installer_output_stem).tar.gz"
}
