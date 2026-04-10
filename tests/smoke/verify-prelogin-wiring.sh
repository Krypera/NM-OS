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
BOOT_PROFILE_SERVICE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-boot-profile.service"
BOOT_PROFILE_SCRIPT="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/boot_profile.py"
BOOT_MARKER_SERVICE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-boot-marker.service"
DISPLAY_MANAGER_DROPIN="${ROOT_DIR}/config/live-build/includes.chroot/etc/systemd/system/display-manager.service.d/nmos-live-user-password.conf"
GREETER_MAIN="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"
GDM_CLIENT="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/gdmclient.py"
GREETER_CLIENT="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/client.py"

for path in "${HOOK_FILE}" "${MODE_FILE}" "${GREETER_DESKTOP_FILE}" "${POSTLOGIN_FILE}" "${POLICY_FILE}" "${TMPFILES_FILE}" "${LIVE_USER_CONFIG}" "${LIVE_USER_PASSWORD_SERVICE}" "${BOOT_PROFILE_SERVICE}" "${BOOT_PROFILE_SCRIPT}" "${BOOT_MARKER_SERVICE}" "${DISPLAY_MANAGER_DROPIN}" "${GREETER_MAIN}" "${GDM_CLIENT}" "${GREETER_CLIENT}"; do
    [ -e "${path}" ] || {
        echo "missing required pre-login asset: ${path}" >&2
        exit 1
    }
done

grep -q 'gdm-shell-nmos' "${HOOK_FILE}" || {
    echo "GDM session hook does not wire the NM-OS greeter into the display-manager session." >&2
    exit 1
}

grep -q '"isGreeter": true' "${MODE_FILE}" || {
    echo "Custom GNOME shell mode is not marked as a greeter session." >&2
    exit 1
}

grep -q 'Debian-gdm' "${POLICY_FILE}" || {
    echo "D-Bus policy does not grant Debian-gdm access to the persistence backend." >&2
    exit 1
}

grep -q 'context="default"' "${POLICY_FILE}" || {
    echo "D-Bus policy does not define a default deny policy for org.nmos.PersistentStorage." >&2
    exit 1
}

grep -q 'deny send_destination="org.nmos.PersistentStorage"' "${POLICY_FILE}" || {
    echo "D-Bus policy does not block non-whitelisted users from the persistence backend." >&2
    exit 1
}

grep -q 'send_interface="org.nmos.PersistentStorage"' "${POLICY_FILE}" || {
    echo "D-Bus policy does not restrict Debian-gdm calls to the NM-OS persistence interface." >&2
    exit 1
}

grep -q '/run/nmos/greeter-state.json' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not consume the greeter runtime handoff file." >&2
    exit 1
}

grep -q 'mapfile -t STATE_VALUES' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not parse greeter state through a fixed-value array handoff." >&2
    exit 1
}

grep -q 'write_runtime_text' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not clear greeter state through the secure runtime helper." >&2
    exit 1
}

if grep -q '\beval\b' "${POSTLOGIN_FILE}"; then
    echo "GDM PostLogin hook still uses eval for the greeter runtime handoff." >&2
    exit 1
fi

grep -q 'localectl set-x11-keymap' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not apply the selected X11 keyboard layout." >&2
    exit 1
}

grep -q '^Exec=/usr/local/bin/nmos-greeter$' "${GREETER_DESKTOP_FILE}" || {
    echo "GDM greeter desktop entry does not launch /usr/local/bin/nmos-greeter." >&2
    exit 1
}

grep -q 'if self.persistence_state.get("busy")' "${GREETER_MAIN}" || {
    echo "Greeter finish flow does not block session start during active persistence operations." >&2
    exit 1
}

grep -q 'self.persistence_password.set_text("")' "${GREETER_MAIN}" || {
    echo "Greeter does not clear persistence passphrases after persistence actions." >&2
    exit 1
}

grep -q 'self.session_start_in_progress = True' "${GREETER_MAIN}" || {
    echo "Greeter does not mark the live session start flow as in-progress before handing off to GDM." >&2
    exit 1
}

grep -q 'if self.session_start_in_progress:' "${GREETER_MAIN}" || {
    echo "Greeter runtime polling does not pause while the live session handoff is in progress." >&2
    exit 1
}

grep -q 'GDM could not start the live session' "${GDM_CLIENT}" || {
    echo "GDM client does not report session start failures from call_start_session_when_ready_sync." >&2
    exit 1
}

grep -q 'introspect=False' "${GREETER_CLIENT}" || {
    echo "Greeter D-Bus client does not disable runtime introspection for the persistence backend." >&2
    exit 1
}

grep -q 'noautologin' "${AUTO_CONFIG_FILE}" || {
    echo "live-build bootappend does not disable live-session autologin." >&2
    exit 1
}

if grep -q 'LIVE_PASSWORD="live"' "${LIVE_USER_CONFIG}"; then
    echo "live user defaults still hardcode LIVE_PASSWORD=live." >&2
    exit 1
fi

grep -q 'generate_live_password' "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/ensure_live_user_password.py" || {
    echo "live user password helper does not generate a per-boot random password." >&2
    exit 1
}

grep -q '/run/nmos/live-user-password' "${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/ensure_live_user_password.py" || {
    echo "live user password helper does not publish the runtime password file for Debian-gdm." >&2
    exit 1
}

grep -q '/run/nmos/live-user-password' "${GDM_CLIENT}" || {
    echo "GDM client does not read the runtime live-user password file." >&2
    exit 1
}

grep -q 'NMOS_BOOT_MODE' "${BOOT_PROFILE_SCRIPT}" || {
    echo "boot profile helper does not emit a boot mode marker." >&2
    exit 1
}

grep -q 'live-user-password' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the runtime live-user password file." >&2
    exit 1
}

grep -q 'boot-mode.json' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the runtime boot mode file." >&2
    exit 1
}

grep -q 'nmos-live-user-password.service' "${ENABLE_UNITS_HOOK}" || {
    echo "live user password service is not enabled in the image." >&2
    exit 1
}

grep -q 'nmos-boot-profile.service' "${ENABLE_UNITS_HOOK}" || {
    echo "boot profile service is not enabled in the image." >&2
    exit 1
}

grep -q 'Before=nmos-network-bootstrap.service' "${BOOT_PROFILE_SERVICE}" || {
    echo "boot profile service does not run before network bootstrap." >&2
    exit 1
}

grep -q 'After=.*nmos-boot-profile.service' "${BOOT_MARKER_SERVICE}" || {
    echo "boot marker service does not wait for the boot profile service." >&2
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
