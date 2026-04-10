#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GREETER_MAIN="${ROOT_DIR}/apps/nmos_greeter/nmos_greeter/main.py"
DESKTOP_ENTRY="${ROOT_DIR}/config/live-build/includes.chroot/usr/share/applications/nmos-greeter.desktop"
GDM_DESKTOP_ENTRY="${ROOT_DIR}/config/live-build/includes.chroot/usr/share/gdm/greeter/applications/nmos-greeter.desktop"

grep -q 'es_ES.UTF-8' "${GREETER_MAIN}" || {
    echo "Greeter language selector does not include Spanish." >&2
    exit 1
}

grep -q '^Name\[es\]=' "${DESKTOP_ENTRY}" || {
    echo "Desktop entry does not expose a Spanish display name." >&2
    exit 1
}

grep -q '^Name\[es\]=' "${GDM_DESKTOP_ENTRY}" || {
    echo "GDM desktop entry does not expose a Spanish display name." >&2
    exit 1
}

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import os
import sys
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
sys.path.insert(0, str(root / "apps" / "nmos_common"))

from nmos_common.i18n import display_language_name, resolve_supported_locale, translate, translate_message

assert resolve_supported_locale("es_MX.UTF-8") == "es_ES.UTF-8"
assert display_language_name("es_ES.UTF-8") == "Espa\u00f1ol"
assert translate("es_ES.UTF-8", "Language") == "Idioma"
assert translate("es_ES.UTF-8", "Finish") == "Finalizar"
assert translate_message("es_ES.UTF-8", "Tor is ready") == "Tor est\u00e1 listo"
assert (
    translate_message("es_ES.UTF-8", "Network is disabled by boot mode (recovery).")
    == "La red est\u00e1 desactivada por el modo de arranque (Recuperaci\u00f3n)."
)
assert translate("de_DE.UTF-8", "Language") == "Language"

print("Greeter i18n checks passed")
PY
