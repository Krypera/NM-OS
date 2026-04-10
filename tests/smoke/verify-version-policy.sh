#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMON_SH="${ROOT_DIR}/build/lib/common.sh"
BUILD_SH="${ROOT_DIR}/build/build.sh"
VERSION_FILE="${ROOT_DIR}/config/version"

VERSION="$(tr -d '\r\n' < "${VERSION_FILE}")"
VERSION_PATTERN='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?$'

if [[ -z "${VERSION}" ]]; then
    echo "config/version is empty." >&2
    exit 1
fi

if [[ ! "${VERSION}" =~ ${VERSION_PATTERN} ]]; then
    echo "config/version has unsupported format: ${VERSION}" >&2
    exit 1
fi

grep -q 'validate_version_format' "${COMMON_SH}" || {
    echo "common build library does not expose validate_version_format." >&2
    exit 1
}

grep -q 'VERSION_PATTERN=' "${COMMON_SH}" || {
    echo "common build library does not define a version pattern." >&2
    exit 1
}

grep -q 'validate_version_format "${VERSION}"' "${BUILD_SH}" || {
    echo "build entry point does not enforce version format validation." >&2
    exit 1
}

echo "Version policy checks passed."
