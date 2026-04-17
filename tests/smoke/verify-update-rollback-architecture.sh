#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCH_DOC="${ROOT_DIR}/docs/update-rollback-architecture.md"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
VERIFY_ARTIFACTS="${ROOT_DIR}/build/verify-artifacts.sh"

for path in "${ARCH_DOC}" "${CONTROL_CENTER_MAIN}" "${VERIFY_ARTIFACTS}"; do
    [ -f "${path}" ] || {
        echo "missing update/rollback architecture dependency: ${path}" >&2
        exit 1
    }
done

grep -q '## Atomic Strategy Decision' "${ARCH_DOC}" || {
    echo "update architecture doc is missing atomic strategy section." >&2
    exit 1
}

grep -q '## Signed Artifact And Manifest Requirements' "${ARCH_DOC}" || {
    echo "update architecture doc is missing signed artifact requirements." >&2
    exit 1
}

grep -q '## Failure Recovery UX' "${ARCH_DOC}" || {
    echo "update architecture doc is missing failure recovery UX section." >&2
    exit 1
}

grep -q '## Release Gate Checklist' "${ARCH_DOC}" || {
    echo "update architecture doc is missing release gate checklist." >&2
    exit 1
}

grep -q 'release-manifest.json' "${ARCH_DOC}" || {
    echo "update architecture doc does not reference release manifest metadata." >&2
    exit 1
}

grep -q 'update-catalog.json' "${ARCH_DOC}" || {
    echo "update architecture doc does not reference update catalog metadata." >&2
    exit 1
}

grep -q 'on_apply_update' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not expose update apply action." >&2
    exit 1
}

grep -q 'on_rollback_update' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not expose rollback action." >&2
    exit 1
}

grep -q 'RELEASE_MANIFEST_JSON_PATH' "${VERIFY_ARTIFACTS}" || {
    echo "artifact verification does not include release manifest checks." >&2
    exit 1
}

grep -q 'UPDATE_CATALOG_PATH' "${VERIFY_ARTIFACTS}" || {
    echo "artifact verification does not include update catalog checks." >&2
    exit 1
}

echo "Update and rollback architecture checks passed."
