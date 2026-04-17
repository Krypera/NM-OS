#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SYSTEM_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/system.py"

for path in "${CONTROL_CENTER_MAIN}" "${SYSTEM_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required update center path: ${path}" >&2
        exit 1
    }
done

for ui_label in \
    'Update center' \
    'Release channel' \
    'Check updates' \
    'Apply update' \
    'Rollback'; do
    grep -q "${ui_label}" "${SYSTEM_PANEL}" || {
        echo "system panel is missing update center label: ${ui_label}" >&2
        exit 1
    }
done

for handler in \
    'def on_update_channel_changed' \
    'def on_check_updates' \
    'def on_apply_update' \
    'def on_rollback_update' \
    'def refresh_update_center' \
    'def _manifest_supports_trusted_updates' \
    'def _manifest_supports_rollback'; do
    grep -q "${handler}" "${CONTROL_CENTER_MAIN}" || {
        echo "control center is missing update handler: ${handler}" >&2
        exit 1
    }
done

for guardrail_line in \
    'Update guardrail:' \
    'Rollback guardrail:' \
    'Update blocked: release manifest metadata is unavailable.' \
    'Rollback blocked: current release policy does not declare rollback support.'; do
    grep -q "${guardrail_line}" "${CONTROL_CENTER_MAIN}" || {
        echo "update center is missing guardrail message: ${guardrail_line}" >&2
        exit 1
    }
done

echo "Update center guardrail checks passed."
