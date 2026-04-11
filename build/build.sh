#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

if [ "$(uname -s)" != "Linux" ]; then
    echo "NM-OS build must run on Linux." >&2
    exit 1
fi

require_cmd rsync
require_cmd tar
require_cmd sha256sum
require_cmd grep
validate_version_format "${VERSION}"

bash "${ROOT_DIR}/build/verify-no-leaks.sh"
stage_system_overlay_tree
stage_installer_assets_tree

ENABLED_FEATURES=()
if [ "${NMOS_ENABLE_BRAVE:-0}" = "1" ]; then
    mkdir -p "${ROOTFS_DIR}/etc/nmos/features"
    cat > "${ROOTFS_DIR}/etc/nmos/features/brave" <<'EOF'
enabled=true
privacy_mode=optional
anonymity_warning=Brave is privacy-focused but not equivalent to Tor Browser anonymity.
EOF
    ENABLED_FEATURES+=("brave")
fi

FEATURES_VALUE="none"
if [ "${#ENABLED_FEATURES[@]}" -gt 0 ]; then
    FEATURES_VALUE="$(IFS=,; echo "${ENABLED_FEATURES[*]}")"
fi

OUTPUT_STEM="$(build_output_stem)"
ARCHIVE_NAME="$(build_archive_name)"
ARCHIVE_PATH="${DIST_DIR}/${ARCHIVE_NAME}"
INSTALLER_STEM="$(installer_output_stem)"
INSTALLER_ARCHIVE_NAME="$(installer_archive_name)"
INSTALLER_ARCHIVE_PATH="${DIST_DIR}/${INSTALLER_ARCHIVE_NAME}"
tar -C "${ROOTFS_DIR}" -czf "${ARCHIVE_PATH}" .
tar -C "${INSTALLER_WORK_DIR}" -czf "${INSTALLER_ARCHIVE_PATH}" .
sha256sum "${ARCHIVE_PATH}" > "${DIST_DIR}/${OUTPUT_STEM}.sha256"
sha256sum "${INSTALLER_ARCHIVE_PATH}" > "${DIST_DIR}/${INSTALLER_STEM}.sha256"
cp "${SYSTEM_PACKAGES_SOURCE}/base.txt" "${DIST_DIR}/${OUTPUT_STEM}.packages"
if [ "${NMOS_ENABLE_BRAVE:-0}" = "1" ]; then
    cat "${SYSTEM_PACKAGES_SOURCE}/optional-brave.txt" >> "${DIST_DIR}/${OUTPUT_STEM}.packages"
fi
if [ -f "${INSTALLER_PACKAGES_SOURCE}/base.txt" ]; then
    cp "${INSTALLER_PACKAGES_SOURCE}/base.txt" "${DIST_DIR}/${INSTALLER_STEM}.packages"
fi

cat > "${DIST_DIR}/${OUTPUT_STEM}.build-manifest" <<EOF
version=${VERSION}
artifact=${ARCHIVE_NAME}
build_host=$(hostname)
built_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
source_repo=https://github.com/Krypera/NM-OS.git
artifact_type=system-overlay
installer_assets=${INSTALLER_ARCHIVE_NAME}
installer_stack=calamares
app_isolation=flatpak-portals
features=${FEATURES_VALUE}
EOF

bash "${ROOT_DIR}/build/verify-artifacts.sh"

echo "Build complete: ${ARCHIVE_PATH}"
