#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REQUIRED=(
    "${ROOT_DIR}/.gitattributes"
    "${ROOT_DIR}/README.md"
    "${ROOT_DIR}/COPYING"
    "${ROOT_DIR}/LICENSE"
    "${ROOT_DIR}/build/build.sh"
    "${ROOT_DIR}/build/build.ps1"
    "${ROOT_DIR}/build/install-deps.ps1"
    "${ROOT_DIR}/build/verify-artifacts.sh"
    "${ROOT_DIR}/config/live-build/auto/config"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/dconf/profile/user"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/gdm3/PostLogin/Default"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/nmos/live-user.conf"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/systemd/system/display-manager.service.d/nmos-live-user-password.conf"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/udev/rules.d/61-nmos-ignore-internal-disks.rules"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-boot-marker.service"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-boot-profile.service"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-live-user-password.service"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/ensure_live_user_password.py"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/boot_profile.py"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/desktop_mode.py"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/share/gdm/greeter/applications/nmos-greeter.desktop"
    "${ROOT_DIR}/config/live-build/includes.chroot/usr/share/gnome-shell/modes/gdm-nmos.json"
    "${ROOT_DIR}/config/live-build/includes.chroot/etc/xdg/autostart/nmos-desktop-mode.desktop"
    "${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/boot_mode.py"
    "${ROOT_DIR}/apps/nmos_common/nmos_common/network_status.py"
    "${ROOT_DIR}/apps/nmos_persistent_storage/nmos_persistent_storage/service.py"
    "${ROOT_DIR}/docs/windows-wsl.md"
    "${ROOT_DIR}/docs/usb-boot-checklist.md"
    "${ROOT_DIR}/tests/smoke/verify-build-hygiene.sh"
    "${ROOT_DIR}/tests/smoke/verify-boot-modes.sh"
    "${ROOT_DIR}/tests/smoke/verify-brave-optional.sh"
    "${ROOT_DIR}/tests/smoke/verify-disk-safety.sh"
    "${ROOT_DIR}/tests/smoke/verify-greeter-state.sh"
    "${ROOT_DIR}/tests/smoke/verify-live-login-config.sh"
    "${ROOT_DIR}/tests/smoke/verify-network-gate-transition.sh"
    "${ROOT_DIR}/tests/smoke/verify-network-status-normalization.sh"
    "${ROOT_DIR}/tests/smoke/verify-persistence-state-machine.sh"
    "${ROOT_DIR}/tests/smoke/verify-prelogin-wiring.sh"
    "${ROOT_DIR}/tests/smoke/verify-runtime-logic.sh"
    "${ROOT_DIR}/hooks/live/040-configure-gdm-session.hook.chroot"
    "${ROOT_DIR}/hooks/live/050-configure-boot-modes.hook.binary"
    "${ROOT_DIR}/hooks/optional/050-install-brave-browser.hook.chroot"
)

for path in "${REQUIRED[@]}"; do
    [ -e "${path}" ] || {
        echo "missing required path: ${path}" >&2
        exit 1
    }
done

command -v git >/dev/null 2>&1 || {
    echo "missing required command: git" >&2
    exit 1
}

CLEAN_ROOM_PATTERN='^(ta'"'"'ils-stable|upstream|private)/'

if git -C "${ROOT_DIR}" ls-files | grep -Eq "${CLEAN_ROOM_PATTERN}"; then
    echo "tracked files found under clean-room excluded directories." >&2
    exit 1
fi

echo "Repository structure looks complete."
