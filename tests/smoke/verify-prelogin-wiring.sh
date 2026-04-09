#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK_FILE="${ROOT_DIR}/hooks/live/040-configure-gdm-session.hook.chroot"
MODE_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/share/gnome-shell/modes/gdm-nmos.json"
GREETER_DESKTOP_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/share/gdm/greeter/applications/nmos-greeter.desktop"
POSTLOGIN_FILE="${ROOT_DIR}/config/live-build/includes.chroot/etc/gdm3/PostLogin/Default"
POLICY_FILE="${ROOT_DIR}/config/live-build/includes.chroot/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf"
TMPFILES_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/tmpfiles.d/nmos.conf"
ENABLE_UNITS_HOOK="${ROOT_DIR}/hooks/live/020-enable-nmos-units.hook.chroot"
LEGACY_USER_UNIT="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/user/nmos-greeter.service"
AUTO_CONFIG_FILE="${ROOT_DIR}/config/live-build/auto/config"
LIVE_USER_CONFIG="${ROOT_DIR}/config/live-build/includes.chroot/etc/nmos/live-user.conf"
LIVE_USER_PASSWORD_SERVICE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-live-user-password.service"
DISPLAY_MANAGER_DROPIN="${ROOT_DIR}/config/live-build/includes.chroot/etc/systemd/system/display-manager.service.d/nmos-live-user-password.conf"

for path in "${HOOK_FILE}" "${MODE_FILE}" "${GREETER_DESKTOP_FILE}" "${POSTLOGIN_FILE}" "${POLICY_FILE}" "${TMPFILES_FILE}" "${LIVE_USER_CONFIG}" "${LIVE_USER_PASSWORD_SERVICE}" "${DISPLAY_MANAGER_DROPIN}"; do
    [ -e "${path}" ] || {
        echo "missing required pre-login asset: ${path}" >&2
        exit 1
    }
done

grep -q 'gdm-shell-nmos' "${HOOK_FILE}" || {
    echo "GDM session hook does not wire the NM-OS greeter into the display-manager session." >&2
    exit 1
}

grep -q 'Debian-gdm' "${POLICY_FILE}" || {
    echo "D-Bus policy does not grant Debian-gdm access to the persistence backend." >&2
    exit 1
}

grep -q '/run/nmos/greeter-state.json' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not consume the greeter runtime handoff file." >&2
    exit 1
}

grep -q 'localectl set-x11-keymap' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not apply the selected X11 keyboard layout." >&2
    exit 1
}

grep -q '^Exec=/usr/local/bin/nmos-greeter$' "${GREETER_DESKTOP_FILE}" || {
    echo "GDM greeter desktop entry does not launch /usr/local/bin/nmos-greeter." >&2
    exit 1
}

grep -q 'noautologin' "${AUTO_CONFIG_FILE}" || {
    echo "live-build bootappend does not disable live-session autologin." >&2
    exit 1
}

grep -q 'LIVE_PASSWORD=' "${LIVE_USER_CONFIG}" || {
    echo "live user defaults do not define a login password for the greeter handoff." >&2
    exit 1
}

grep -q 'nmos-live-user-password.service' "${ENABLE_UNITS_HOOK}" || {
    echo "live user password service is not enabled in the image." >&2
    exit 1
}

grep -q 'Before=display-manager.service' "${LIVE_USER_PASSWORD_SERVICE}" || {
    echo "live user password service does not run before the display manager." >&2
    exit 1
}

grep -q 'Wants=nmos-live-user-password.service' "${DISPLAY_MANAGER_DROPIN}" || {
    echo "display-manager override does not wait for the live user password service." >&2
    exit 1
}

grep -q 'greeter-state.json' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the greeter runtime state file." >&2
    exit 1
}

if grep -q 'nmos-greeter.service' "${ENABLE_UNITS_HOOK}"; then
    echo "legacy user-session greeter wiring is still enabled." >&2
    exit 1
fi

if [ -e "${LEGACY_USER_UNIT}" ]; then
    echo "legacy user-session greeter unit still exists." >&2
    exit 1
fi

echo "Pre-login greeter wiring looks configured."
