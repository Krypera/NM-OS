#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOT_HOOK="${ROOT_DIR}/hooks/live/050-configure-boot-modes.hook.binary"
GRUB_TEMPLATE="${ROOT_DIR}/hooks/live/templates/grub-boot-modes.cfg.template"
SYSLINUX_TEMPLATE="${ROOT_DIR}/hooks/live/templates/syslinux-boot-modes.cfg.template"
BOOT_MODE_SERVICE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/systemd/system/nmos-boot-profile.service"
BOOT_MODE_SCRIPT="${ROOT_DIR}/config/live-build/includes.chroot/usr/local/lib/nmos/boot_profile.py"
BOOT_MODE_MODULE="${ROOT_DIR}/apps/nmos_common/nmos_common/boot_mode.py"
TMPFILES_FILE="${ROOT_DIR}/config/live-build/includes.chroot/usr/lib/tmpfiles.d/nmos.conf"
GREETER_MAIN="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"

for path in "${BOOT_HOOK}" "${GRUB_TEMPLATE}" "${SYSLINUX_TEMPLATE}" "${BOOT_MODE_SERVICE}" "${BOOT_MODE_SCRIPT}" "${BOOT_MODE_MODULE}" "${TMPFILES_FILE}" "${GREETER_MAIN}"; do
    [ -f "${path}" ] || {
        echo "missing boot-mode path: ${path}" >&2
        exit 1
    }
done

grep -q 'render_template "${GRUB_TEMPLATE}" "${GRUB_CFG}"' "${BOOT_HOOK}" || {
    echo "boot hook does not render grub menu from template." >&2
    exit 1
}
grep -q 'render_template "${SYSLINUX_TEMPLATE}" "${SYSLINUX_CFG}"' "${BOOT_HOOK}" || {
    echo "boot hook does not render syslinux menu from template." >&2
    exit 1
}
grep -q '__KERNEL__' "${GRUB_TEMPLATE}" || {
    echo "grub template is missing kernel placeholder." >&2
    exit 1
}
grep -q '__OPTIONS__' "${GRUB_TEMPLATE}" || {
    echo "grub template is missing options placeholder." >&2
    exit 1
}
grep -q 'NM-OS (Strict)' "${GRUB_TEMPLATE}" || {
    echo "grub template does not define strict menu entry." >&2
    exit 1
}
grep -q 'NM-OS (Flexible)' "${GRUB_TEMPLATE}" || {
    echo "grub template does not define flexible menu entry." >&2
    exit 1
}
grep -q 'NM-OS (Offline)' "${GRUB_TEMPLATE}" || {
    echo "grub template does not define offline menu entry." >&2
    exit 1
}
grep -q 'NM-OS (Recovery)' "${GRUB_TEMPLATE}" || {
    echo "grub template does not define recovery menu entry." >&2
    exit 1
}
grep -q 'NM-OS (Hardware Compatibility)' "${GRUB_TEMPLATE}" || {
    echo "grub template does not define compatibility menu entry." >&2
    exit 1
}
grep -q 'nmos.mode=compat nomodeset' "${GRUB_TEMPLATE}" || {
    echo "grub compat entry is missing nomodeset or the nmos.mode flag." >&2
    exit 1
}
grep -q 'NM-OS (Strict)' "${SYSLINUX_TEMPLATE}" || {
    echo "syslinux template does not define strict menu entry." >&2
    exit 1
}
grep -q 'NM-OS (Hardware Compatibility)' "${SYSLINUX_TEMPLATE}" || {
    echo "syslinux template does not define compatibility menu entry." >&2
    exit 1
}
grep -q 'nmos.mode=compat nomodeset' "${SYSLINUX_TEMPLATE}" || {
    echo "syslinux compat entry is missing nomodeset or the nmos.mode flag." >&2
    exit 1
}
grep -q '/run/nmos/boot-mode.json' "${TMPFILES_FILE}" || {
    echo "tmpfiles configuration does not provision /run/nmos/boot-mode.json." >&2
    exit 1
}
grep -q 'read_boot_mode_profile' "${GREETER_MAIN}" || {
    echo "greeter does not read the runtime boot mode profile." >&2
    exit 1
}

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
module_path = root / "apps" / "nmos_common" / "nmos_common" / "boot_mode.py"
spec = importlib.util.spec_from_file_location("boot_mode", module_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

assert module.normalize_boot_mode("strict") == "strict"
assert module.normalize_boot_mode("offline") == "offline"
assert module.normalize_boot_mode("UNKNOWN") == "strict"
assert module.parse_mode_from_cmdline("quiet splash nmos.mode=flexible") == "flexible"
assert module.parse_mode_from_cmdline("quiet splash nmos.mode=invalid") == "strict"
assert module.boot_mode_profile("compat")["compat_enabled"] is True
assert module.boot_mode_profile("offline")["network_policy"] == "disabled"
assert module.boot_mode_profile("recovery")["recovery_mode"] is True
PY

echo "Boot mode wiring looks configured."
