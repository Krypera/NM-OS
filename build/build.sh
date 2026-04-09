#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

if [ "$(uname -s)" != "Linux" ]; then
    echo "NM-OS build must run on Linux." >&2
    exit 1
fi

require_cmd rsync
require_cmd lb
require_cmd sha256sum
require_cmd grep
require_cmd cp

"${ROOT_DIR}/build/verify-no-leaks.sh"
stage_live_build_tree

pushd "${WORK_DIR}" >/dev/null
lb clean --purge || true
./auto/config
./auto/build
popd >/dev/null

ISO_SOURCE="$(find_built_iso)"
if [ -z "${ISO_SOURCE}" ]; then
    echo "live-build did not produce an ISO image." >&2
    exit 1
fi

OUTPUT_STEM="$(build_output_stem)"
ISO_NAME="$(build_iso_name)"
IMG_NAME="$(build_img_name)"
ISO_TARGET="${DIST_DIR}/${ISO_NAME}"
IMG_TARGET="${DIST_DIR}/${IMG_NAME}"
cp "${ISO_SOURCE}" "${ISO_TARGET}"

# iso-hybrid images are raw-disk compatible, so we publish the same bytes
# as the primary Windows/Rufus-friendly .img artifact.
cp "${ISO_SOURCE}" "${IMG_TARGET}"
sha256sum "${IMG_TARGET}" "${ISO_TARGET}" > "${DIST_DIR}/${OUTPUT_STEM}.sha256"

if [ -f "${WORK_DIR}/binary.packages" ]; then
    cp "${WORK_DIR}/binary.packages" "${DIST_DIR}/${OUTPUT_STEM}.packages"
else
    cat "${WORK_DIR}/config/package-lists/"*.list.chroot > "${DIST_DIR}/${OUTPUT_STEM}.packages"
fi

cat > "${DIST_DIR}/${OUTPUT_STEM}.build-manifest" <<EOF
version=${VERSION}
img=${IMG_NAME}
iso=${ISO_NAME}
build_host=$(hostname)
built_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
source_repo=https://github.com/Krypera/NM-OS.git
EOF

"${ROOT_DIR}/build/verify-artifacts.sh"

echo "Build complete: ${IMG_TARGET} and ${ISO_TARGET}"
