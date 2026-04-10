#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_SH="${ROOT_DIR}/build/build.sh"
BUILD_PS1="${ROOT_DIR}/build/build.ps1"
BRAVE_HOOK="${ROOT_DIR}/hooks/optional/050-install-brave-browser.hook.chroot"
DESKTOP_MODE_SCRIPT="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/desktop_mode.py"
AUTOSTART_FILE="${ROOT_DIR}/config/live-build/includes.chroot/etc/xdg/autostart/nmos-desktop-mode.desktop"
BRAVE_POLICY_SCRIPT="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/brave_policy.py"

[ -f "${BRAVE_HOOK}" ] || {
    echo "optional Brave hook is missing." >&2
    exit 1
}

[ -f "${BRAVE_POLICY_SCRIPT}" ] || {
    echo "Brave policy runtime helper is missing." >&2
    exit 1
}

grep -q 'NMOS_ENABLE_BRAVE' "${BUILD_SH}" || {
    echo "build.sh does not support NMOS_ENABLE_BRAVE optional feature toggle." >&2
    exit 1
}

grep -q 'hooks/optional/050-install-brave-browser.hook.chroot' "${BUILD_SH}" || {
    echo "build.sh does not stage the optional Brave hook." >&2
    exit 1
}

grep -q 'features=' "${BUILD_SH}" || {
    echo "build manifest does not record enabled optional features." >&2
    exit 1
}

grep -q 'EnableBrave' "${BUILD_PS1}" || {
    echo "build.ps1 does not expose the EnableBrave switch." >&2
    exit 1
}

grep -q 'not equivalent to Tor Browser anonymity' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not include the anonymity warning note." >&2
    exit 1
}

grep -q 'mode == "flexible"' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not keep Brave visible in flexible mode." >&2
    exit 1
}

grep -q 'load_feature_flag' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not use shared feature-flag parsing." >&2
    exit 1
}

grep -q 'NoDisplay=true' "${DESKTOP_MODE_SCRIPT}" || {
    echo "desktop mode helper does not hide Brave entries outside flexible mode." >&2
    exit 1
}

grep -q 'Exec=/usr/local/lib/nmos/desktop_mode.py' "${AUTOSTART_FILE}" || {
    echo "desktop mode policy helper is not wired into desktop autostart." >&2
    exit 1
}

grep -q 'ALLOWED_MODES = {"flexible"}' "${BRAVE_POLICY_SCRIPT}" || {
    echo "Brave policy helper does not enforce the flexible-mode allowlist." >&2
    exit 1
}

grep -q 'load_feature_flag' "${BRAVE_POLICY_SCRIPT}" || {
    echo "Brave policy helper does not use shared feature-flag parsing." >&2
    exit 1
}

grep -q 'install_binary_policy_wrapper' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not install binary policy wrappers." >&2
    exit 1
}

grep -q '/usr/local/lib/nmos/brave_policy.py' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not route Brave launch through the runtime policy helper." >&2
    exit 1
}

grep -q '\.real' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not preserve original Brave binaries behind a wrapper." >&2
    exit 1
}

grep -q 'ALLOWED_BRAVE_FINGERPRINTS' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not pin Brave signing key fingerprints." >&2
    exit 1
}

grep -q 'verify_brave_keyring_fingerprint' "${BRAVE_HOOK}" || {
    echo "optional Brave hook does not verify the keyring fingerprint." >&2
    exit 1
}

echo "Optional Brave feature wiring looks configured."
