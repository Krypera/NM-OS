#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE_FILE="${ROOT_DIR}/config/system-overlay/usr/share/gnome-shell/modes/gdm-nmos.json"
GREETER_DESKTOP_FILE="${ROOT_DIR}/config/system-overlay/usr/share/gdm/greeter/applications/nmos-greeter.desktop"
GDM_SHELL_FILE="${ROOT_DIR}/config/system-overlay/usr/share/gdm/greeter/applications/gdm-shell-nmos.desktop"
SESSION_FILE="${ROOT_DIR}/config/system-overlay/usr/share/gnome-session/sessions/gdm-nmos.session"
POSTLOGIN_FILE="${ROOT_DIR}/config/system-overlay/etc/gdm3/PostLogin/Default"
POLICY_FILE="${ROOT_DIR}/config/system-overlay/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf"
SETTINGS_POLICY_FILE="${ROOT_DIR}/config/system-overlay/etc/dbus-1/system.d/org.nmos.Settings1.conf"
TMPFILES_FILE="${ROOT_DIR}/config/system-overlay/usr/lib/tmpfiles.d/nmos.conf"
COMMON_SH="${ROOT_DIR}/build/lib/common.sh"

for path in "${MODE_FILE}" "${GREETER_DESKTOP_FILE}" "${GDM_SHELL_FILE}" "${SESSION_FILE}" "${POSTLOGIN_FILE}" "${POLICY_FILE}" "${SETTINGS_POLICY_FILE}" "${TMPFILES_FILE}" "${COMMON_SH}"; do
    [ -e "${path}" ] || {
        echo "missing required pre-login asset: ${path}" >&2
        exit 1
    }
done

grep -q '"isGreeter": true' "${MODE_FILE}" || {
    echo "Custom GNOME shell mode is not marked as a greeter session." >&2
    exit 1
}

grep -q 'Exec=/usr/local/bin/nmos-greeter' "${GREETER_DESKTOP_FILE}" || {
    echo "GDM greeter desktop entry does not launch /usr/local/bin/nmos-greeter." >&2
    exit 1
}

grep -q 'Exec=/usr/bin/gnome-shell --mode=gdm-nmos' "${GDM_SHELL_FILE}" || {
    echo "GDM shell desktop entry does not launch GNOME Shell in gdm-nmos mode." >&2
    exit 1
}

grep -q 'RequiredComponents=gdm-shell-nmos;nmos-greeter;' "${SESSION_FILE}" || {
    echo "GDM session does not require the setup assistant session components." >&2
    exit 1
}

grep -q '/run/nmos/greeter-state.json' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not consume the greeter runtime handoff file." >&2
    exit 1
}

grep -q 'write_runtime_text' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not clear greeter state through the secure runtime helper." >&2
    exit 1
}

grep -q 'logger -t nmos-postlogin' "${POSTLOGIN_FILE}" || {
    echo "GDM PostLogin hook does not log localectl failures to journald." >&2
    exit 1
}

grep -q '@NMOS_GDM_USER@' "${POLICY_FILE}" || {
    echo "D-Bus persistence policy is not platform-adapter aware." >&2
    exit 1
}

grep -q '@NMOS_GDM_USER@' "${SETTINGS_POLICY_FILE}" || {
    echo "D-Bus settings policy is not platform-adapter aware." >&2
    exit 1
}

grep -q 'system-settings.json' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the runtime system settings file." >&2
    exit 1
}

grep -q 'applied-system-settings.json' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision the applied settings runtime file." >&2
    exit 1
}

grep -q 'enable_system_service "nmos-settings.service"' "${COMMON_SH}" || {
    echo "build staging does not enable the settings service." >&2
    exit 1
}

grep -q 'enable_system_service "nmos-settings-bootstrap.service"' "${COMMON_SH}" || {
    echo "build staging does not enable the settings bootstrap service." >&2
    exit 1
}

if grep -q 'live-user-password' "${TMPFILES_FILE}"; then
    echo "tmpfiles configuration still contains legacy password wiring." >&2
    exit 1
fi

echo "Pre-login greeter wiring looks configured."
