#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMON_SH="${ROOT_DIR}/build/lib/common.sh"
GITATTRIBUTES="${ROOT_DIR}/.gitattributes"

command -v git >/dev/null 2>&1 || {
    echo "missing required command: git" >&2
    exit 1
}

grep -Fq -- "--exclude '__pycache__/'" "${COMMON_SH}" || {
    echo "build staging does not exclude __pycache__ directories." >&2
    exit 1
}

grep -Fq -- "--exclude '*.pyc'" "${COMMON_SH}" || {
    echo "build staging does not exclude .pyc files." >&2
    exit 1
}

grep -Fq -- "--exclude '*.pyo'" "${COMMON_SH}" || {
    echo "build staging does not exclude .pyo files." >&2
    exit 1
}

grep -q "staged system overlay tree contains Python cache artifacts" "${COMMON_SH}" || {
    echo "build staging does not fail closed on Python cache artifacts." >&2
    exit 1
}

grep -q 'stage_installer_assets_tree' "${COMMON_SH}" || {
    echo "build helpers do not stage installer assets." >&2
    exit 1
}

grep -q 'resolve_base_installer_iso' "${COMMON_SH}" || {
    echo "build helpers do not resolve the base installer ISO." >&2
    exit 1
}

grep -q 'build_installer_iso_image' "${COMMON_SH}" || {
    echo "build helpers do not expose the installer ISO builder." >&2
    exit 1
}

grep -Fq 'config/system-overlay/usr/local/bin/* text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for overlay launchers." >&2
    exit 1
}

grep -Fq 'config/system-overlay/etc/gdm3/PostLogin/* text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for GDM PostLogin hooks." >&2
    exit 1
}

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import os
import subprocess
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
tracked = subprocess.check_output(["git", "-C", str(root), "ls-files"], text=True).splitlines()
lf_patterns = (".sh", ".py", ".service", ".target", ".conf", ".desktop", ".json", ".md", ".yml", ".toml", ".css", ".in")
lf_violations: list[str] = []

for rel in tracked:
    path = root / rel
    if not path.is_file():
        continue
    data = path.read_bytes()
    if rel.endswith(lf_patterns) and b"\r\n" in data:
        lf_violations.append(rel)

if lf_violations:
    raise SystemExit("LF policy violation in: " + ", ".join(sorted(lf_violations)))
PY

echo "Build hygiene checks passed"
