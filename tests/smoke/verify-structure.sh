#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REQUIRED=(
    "${ROOT_DIR}/.gitattributes"
    "${ROOT_DIR}/.github/workflows/smoke.yml"
    "${ROOT_DIR}/.shellcheckrc"
    "${ROOT_DIR}/README.md"
    "${ROOT_DIR}/COPYING"
    "${ROOT_DIR}/LICENSE"
    "${ROOT_DIR}/pyproject.toml"
    "${ROOT_DIR}/build/build.sh"
    "${ROOT_DIR}/build/install-dev-deps.sh"
    "${ROOT_DIR}/build/build.ps1"
    "${ROOT_DIR}/build/install-deps.ps1"
    "${ROOT_DIR}/build/smoke-overlay.sh"
    "${ROOT_DIR}/build/verify-artifacts.sh"
    "${ROOT_DIR}/config/system-overlay/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf"
    "${ROOT_DIR}/config/system-overlay/etc/dbus-1/system.d/org.nmos.Settings1.conf"
    "${ROOT_DIR}/config/system-overlay/etc/gdm3/PostLogin/Default"
    "${ROOT_DIR}/config/system-overlay/etc/xdg/autostart/nmos-desktop-mode.desktop"
    "${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-settings.service"
    "${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-settings-bootstrap.service"
    "${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-boot-marker.service"
    "${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-network-bootstrap.service"
    "${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-persistent-storage.service"
    "${ROOT_DIR}/config/system-overlay/usr/lib/tmpfiles.d/nmos.conf"
    "${ROOT_DIR}/config/system-overlay/usr/local/bin/nmos-control-center"
    "${ROOT_DIR}/config/system-overlay/usr/local/bin/nmos-settings-service"
    "${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/settings_bootstrap.py"
    "${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/network_bootstrap.py"
    "${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/desktop_mode.py"
    "${ROOT_DIR}/config/system-overlay/usr/local/lib/nmos/brave_policy.py"
    "${ROOT_DIR}/config/system-overlay/usr/share/applications/nmos-control-center.desktop"
    "${ROOT_DIR}/config/system-overlay/usr/share/gdm/greeter/applications/nmos-greeter.desktop"
    "${ROOT_DIR}/config/system-overlay/usr/share/gdm/greeter/applications/gdm-shell-nmos.desktop"
    "${ROOT_DIR}/config/system-overlay/usr/share/gnome-session/sessions/gdm-nmos.session"
    "${ROOT_DIR}/config/system-overlay/usr/share/nmos/theme/nmos.css"
    "${ROOT_DIR}/config/installer/calamares/settings.conf"
    "${ROOT_DIR}/config/installer/calamares/branding/nmos/branding.desc"
    "${ROOT_DIR}/config/installer/debian-installer/preseed/nmos.cfg.in"
    "${ROOT_DIR}/config/installer/debian-installer/preseed/install-overlay.sh.in"
    "${ROOT_DIR}/config/installer-packages/base.txt"
    "${ROOT_DIR}/config/system-packages/base.txt"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/system_settings.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/settings_client.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/ui_theme.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/config_helpers.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/i18n.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/network_status.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/runtime_state.py"
    "${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/network_model.py"
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/persistence_actions.py"
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/ui_composition.py"
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/mount_crypto_ops.py"
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/state_serialization.py"
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/storage.py"
    "${ROOT_DIR}/apps/nmos_settings/nmos_settings/service.py"
    "${ROOT_DIR}/docs/build.md"
    "${ROOT_DIR}/docs/runtime.md"
    "${ROOT_DIR}/docs/security-profiles.md"
    "${ROOT_DIR}/docs/translations.md"
    "${ROOT_DIR}/docs/windows-wsl.md"
    "${ROOT_DIR}/tests/python/conftest.py"
    "${ROOT_DIR}/tests/python/test_compile_sources.py"
    "${ROOT_DIR}/tests/python/test_runtime_logic.py"
    "${ROOT_DIR}/tests/smoke/verify-build-hygiene.sh"
    "${ROOT_DIR}/tests/smoke/verify-brave-optional.sh"
    "${ROOT_DIR}/tests/smoke/verify-control-center.sh"
    "${ROOT_DIR}/tests/smoke/verify-greeter-i18n.sh"
    "${ROOT_DIR}/tests/smoke/verify-greeter-state.sh"
    "${ROOT_DIR}/tests/smoke/verify-installer-media.sh"
    "${ROOT_DIR}/tests/smoke/verify-network-policy.sh"
    "${ROOT_DIR}/tests/smoke/verify-prelogin-wiring.sh"
    "${ROOT_DIR}/tests/smoke/verify-quality-tooling.sh"
    "${ROOT_DIR}/tests/smoke/verify-runtime-logic.sh"
    "${ROOT_DIR}/tests/smoke/verify-settings-model.sh"
    "${ROOT_DIR}/tests/smoke/verify-systemd-hardening.sh"
    "${ROOT_DIR}/tests/smoke/verify-vault-storage.sh"
    "${ROOT_DIR}/tests/smoke/verify-windows-wsl-bridge.ps1"
)

for path in "${REQUIRED[@]}"; do
    [ -e "${path}" ] || {
        echo "missing required path: ${path}" >&2
        exit 1
    }
done

for removed_path in \
    "${ROOT_DIR}/config/live-build" \
    "${ROOT_DIR}/hooks/live" \
    "${ROOT_DIR}/hooks/optional/050-install-brave-browser.hook.chroot" \
    "${ROOT_DIR}/apps/nmos_common/nmos_common/boot_mode.py" \
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/gdmclient.py" \
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/gdm_handoff.py" \
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/disk_discovery.py" \
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/partition_planning.py" \
    "${ROOT_DIR}/tests/smoke/verify-boot-modes.sh" \
    "${ROOT_DIR}/tests/smoke/verify-live-login-config.sh"; do
    if [ -e "${removed_path}" ]; then
        echo "live-only path still exists: ${removed_path}" >&2
        exit 1
    fi
done

command -v git >/dev/null 2>&1 || {
    echo "missing required command: git" >&2
    exit 1
}

echo "Repository structure looks complete."
