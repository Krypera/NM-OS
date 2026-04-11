#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL_CENTER_MAIN="${ROOT_DIR}/apps/nmos_control_center/nmos_control_center/main.py"
SETTINGS_SERVICE="${ROOT_DIR}/apps/nmos_settings/nmos_settings/service.py"
SETTINGS_POLICY="${ROOT_DIR}/config/system-overlay/etc/dbus-1/system.d/org.nmos.Settings1.conf"
SETTINGS_UNIT="${ROOT_DIR}/config/system-overlay/usr/lib/systemd/system/nmos-settings.service"
CONTROL_CENTER_DESKTOP="${ROOT_DIR}/config/system-overlay/usr/share/applications/nmos-control-center.desktop"
THEME_CSS="${ROOT_DIR}/config/system-overlay/usr/share/nmos/theme/nmos.css"
INSTALLER_SETTINGS="${ROOT_DIR}/config/installer/calamares/settings.conf"
INSTALLER_BRANDING="${ROOT_DIR}/config/installer/calamares/branding/nmos/branding.desc"

for path in \
    "${CONTROL_CENTER_MAIN}" \
    "${SETTINGS_SERVICE}" \
    "${SETTINGS_POLICY}" \
    "${SETTINGS_UNIT}" \
    "${CONTROL_CENTER_DESKTOP}" \
    "${THEME_CSS}" \
    "${INSTALLER_SETTINGS}" \
    "${INSTALLER_BRANDING}"; do
    [ -f "${path}" ] || {
        echo "missing control-center or installer asset: ${path}" >&2
        exit 1
    }
done

grep -q 'NM-OS Control Center' "${CONTROL_CENTER_MAIN}" || {
    echo "control center does not expose the expected product title." >&2
    exit 1
}

grep -q 'Profiles' "${CONTROL_CENTER_MAIN}" || {
    echo "control center is missing the profiles section." >&2
    exit 1
}

grep -q 'Appearance' "${CONTROL_CENTER_MAIN}" || {
    echo "control center is missing the appearance section." >&2
    exit 1
}

grep -q 'org.nmos.Settings1' "${SETTINGS_SERVICE}" || {
    echo "settings service does not expose org.nmos.Settings1." >&2
    exit 1
}

grep -q '^Exec=/usr/local/bin/nmos-control-center$' "${CONTROL_CENTER_DESKTOP}" || {
    echo "control center desktop entry does not point at the launcher." >&2
    exit 1
}

grep -q '^ExecStart=/usr/local/bin/nmos-settings-service$' "${SETTINGS_UNIT}" || {
    echo "settings systemd unit does not launch the settings service." >&2
    exit 1
}

grep -q '^  <allow send_destination="org.nmos.Settings1"' "${SETTINGS_POLICY}" || {
    echo "settings D-Bus policy does not allow sending to org.nmos.Settings1." >&2
    exit 1
}

grep -q '.nmos-root' "${THEME_CSS}" || {
    echo "shared theme CSS does not define the NM-OS root class." >&2
    exit 1
}

grep -q '^branding: nmos$' "${INSTALLER_SETTINGS}" || {
    echo "Calamares settings do not point at NM-OS branding." >&2
    exit 1
}

grep -q 'productName: "NM-OS"' "${INSTALLER_BRANDING}" || {
    echo "installer branding does not declare the NM-OS product name." >&2
    exit 1
}

echo "Control center and installer scaffolding look configured."
