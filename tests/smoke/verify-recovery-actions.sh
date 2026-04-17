#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SYSTEM_PANEL="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/panels/system.py"

for path in "${CONTROL_CENTER_MAIN}" "${SYSTEM_PANEL}"; do
    [ -f "${path}" ] || {
        echo "missing required recovery action path: ${path}" >&2
        exit 1
    }
done

for ui_label in \
    'Recovery actions' \
    'Create diagnostics bundle' \
    'Rollback last settings'; do
    grep -q "${ui_label}" "${SYSTEM_PANEL}" || {
        echo "system panel is missing recovery UI label: ${ui_label}" >&2
        exit 1
    }
done

for handler in \
    'def build_diagnostics_bundle' \
    'def on_create_diagnostics_bundle' \
    'def snapshot_current_settings' \
    'def load_settings_snapshot' \
    'def on_rollback_settings_snapshot' \
    'def format_recovery_status'; do
    grep -q "${handler}" "${CONTROL_CENTER_MAIN}" || {
        echo "control center is missing recovery handler: ${handler}" >&2
        exit 1
    }
done

for runtime_artifact in \
    'recovery-diagnostics.json' \
    'settings-rollback-snapshot.json' \
    '"bundle_id"' \
    '"history_tail"' \
    'Rollback snapshot:' \
    'Recovery guidance:'; do
    grep -q "${runtime_artifact}" "${CONTROL_CENTER_MAIN}" || {
        echo "recovery implementation is missing required artifact/wiring: ${runtime_artifact}" >&2
        exit 1
    }
done

echo "Recovery action checks passed."
