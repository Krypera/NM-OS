#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECURITY_MODEL_DOC="${ROOT_DIR}/docs/security-model.md"

[ -f "${SECURITY_MODEL_DOC}" ] || {
    echo "missing security model document: ${SECURITY_MODEL_DOC}" >&2
    exit 1
}

grep -q '## Setting To Enforcement Matrix' "${SECURITY_MODEL_DOC}" || {
    echo "security model is missing Setting To Enforcement Matrix." >&2
    exit 1
}

for setting in \
    '`network_policy`' \
    '`sandbox_default`' \
    '`app_overrides`' \
    '`device_policy`' \
    '`logging_policy`' \
    '`allow_brave_browser`' \
    '`default_browser`' \
    '`vault`' \
    '`active_profile`'; do
    grep -q "${setting}" "${SECURITY_MODEL_DOC}" || {
        echo "security model matrix missing required setting row: ${setting}" >&2
        exit 1
    }
done

for enforcement in \
    'network_bootstrap.py' \
    'app_isolation_policy.py' \
    'device_policy.py' \
    'logging_policy.py' \
    'desktop_mode.py'; do
    grep -q "${enforcement}" "${SECURITY_MODEL_DOC}" || {
        echo "security model matrix missing enforcement reference: ${enforcement}" >&2
        exit 1
    }
done

grep -q 'release gate aid' "${SECURITY_MODEL_DOC}" || {
    echo "security model does not declare the matrix as a release gate aid." >&2
    exit 1
}

echo "Security matrix release-gate checks passed."
