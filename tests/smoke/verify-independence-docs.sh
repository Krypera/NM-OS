#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INDEPENDENCE_DIR="${ROOT_DIR}/docs/independence"
README_PATH="${INDEPENDENCE_DIR}/README.md"

REQUIRED_DOCS=(
    "${INDEPENDENCE_DIR}/README.md"
    "${INDEPENDENCE_DIR}/00-goal-and-adr.md"
    "${INDEPENDENCE_DIR}/01-debian-dependency-inventory.md"
    "${INDEPENDENCE_DIR}/02-modular-architecture.md"
    "${INDEPENDENCE_DIR}/03-packaging-strategy.md"
    "${INDEPENDENCE_DIR}/04-image-build-architecture.md"
    "${INDEPENDENCE_DIR}/05-installer-redesign.md"
    "${INDEPENDENCE_DIR}/06-update-release-architecture.md"
    "${INDEPENDENCE_DIR}/07-security-trust-chain.md"
    "${INDEPENDENCE_DIR}/08-hardware-validation-roadmap.md"
    "${INDEPENDENCE_DIR}/09-recovery-supportability.md"
    "${INDEPENDENCE_DIR}/10-qa-release-gates.md"
    "${INDEPENDENCE_DIR}/11-roadmap-12-months.md"
    "${INDEPENDENCE_DIR}/12-first-sprint.md"
)

REQUIRED_TEMPLATES=(
    "${INDEPENDENCE_DIR}/templates/platform-adapter-contract.md"
    "${INDEPENDENCE_DIR}/templates/package-template.yaml"
    "${INDEPENDENCE_DIR}/templates/package-set-template.yaml"
    "${INDEPENDENCE_DIR}/templates/image-definition-template.yaml"
    "${INDEPENDENCE_DIR}/templates/sample-desktop-image.yaml"
    "${INDEPENDENCE_DIR}/templates/sample-installer-image.yaml"
    "${INDEPENDENCE_DIR}/templates/release-manifest-template.json"
    "${INDEPENDENCE_DIR}/templates/signing-policy-template.md"
    "${INDEPENDENCE_DIR}/templates/rc-gate-checklist.md"
    "${INDEPENDENCE_DIR}/templates/dependency-replacement-tracker.md"
    "${INDEPENDENCE_DIR}/templates/phase-board-template.md"
)

for path in "${REQUIRED_DOCS[@]}" "${REQUIRED_TEMPLATES[@]}"; do
    [ -f "${path}" ] || {
        echo "missing independence program file: ${path}" >&2
        exit 1
    }
done

for marker in \
    "00-goal-and-adr.md" \
    "01-debian-dependency-inventory.md" \
    "02-modular-architecture.md" \
    "03-packaging-strategy.md" \
    "04-image-build-architecture.md" \
    "05-installer-redesign.md" \
    "06-update-release-architecture.md" \
    "07-security-trust-chain.md" \
    "08-hardware-validation-roadmap.md" \
    "09-recovery-supportability.md" \
    "10-qa-release-gates.md" \
    "11-roadmap-12-months.md" \
    "12-first-sprint.md"; do
    grep -q "${marker}" "${README_PATH}" || {
        echo "independence README does not link: ${marker}" >&2
        exit 1
    }
done

grep -q "Fact / Inference / Assumption" "${INDEPENDENCE_DIR}/00-goal-and-adr.md" || {
    echo "ADR document is missing Fact / Inference / Assumption notes." >&2
    exit 1
}

echo "Independence program docs look complete."

