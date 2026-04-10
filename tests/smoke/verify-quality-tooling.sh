#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QUALITY_CONFIG="${ROOT_DIR}/pyproject.toml"
SHELLCHECK_CONFIG="${ROOT_DIR}/.shellcheckrc"

[ -f "${QUALITY_CONFIG}" ] || {
    echo "missing quality config: ${QUALITY_CONFIG}" >&2
    exit 1
}

[ -f "${SHELLCHECK_CONFIG}" ] || {
    echo "missing shellcheck config: ${SHELLCHECK_CONFIG}" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || {
    echo "missing required command: git" >&2
    exit 1
}

command -v ruff >/dev/null 2>&1 || {
    echo "missing required command: ruff" >&2
    exit 1
}

command -v shellcheck >/dev/null 2>&1 || {
    echo "missing required command: shellcheck" >&2
    exit 1
}

mapfile -t PYTHON_FILES < <(cd "${ROOT_DIR}" && git ls-files '*.py')
[ "${#PYTHON_FILES[@]}" -gt 0 ] || {
    echo "no Python files found for Ruff checks." >&2
    exit 1
}

(
    cd "${ROOT_DIR}"
    ruff check "${PYTHON_FILES[@]}"
)

mapfile -t SHELL_FILES < <(
    cd "${ROOT_DIR}" && git ls-files \
        '*.sh' \
        '*.hook.chroot' \
        '*.hook.binary' \
        'config/live-build/auto/*' \
        'config/live-build/includes.chroot/usr/local/bin/*' \
        'config/live-build/includes.chroot/etc/gdm3/PostLogin/*'
)
[ "${#SHELL_FILES[@]}" -gt 0 ] || {
    echo "no shell files found for ShellCheck." >&2
    exit 1
}

(
    cd "${ROOT_DIR}"
    shellcheck --severity=error --external-sources --exclude=SC1091 "${SHELL_FILES[@]}"
)

echo "Quality tooling checks passed"
