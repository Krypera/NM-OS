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

grep -q "staged live-build tree contains Python cache artifacts" "${COMMON_SH}" || {
    echo "build staging does not fail closed on Python cache artifacts." >&2
    exit 1
}

grep -Fq "if [ -d \"\${WORK_DIR}/config/includes.chroot/usr/local/bin\" ]; then" "${COMMON_SH}" || {
    echo "build staging does not guard chmod scans for usr/local/bin." >&2
    exit 1
}

grep -Fq "find \"\${WORK_DIR}/config/hooks/live\" -type f -name \"*.hook.binary\" -exec chmod +x {} +" "${COMMON_SH}" || {
    echo "build staging does not mark binary hooks executable." >&2
    exit 1
}

grep -Fq "if [ -d \"\${WORK_DIR}/config/includes.chroot/usr/local/lib/nmos\" ]; then" "${COMMON_SH}" || {
    echo "build staging does not guard chmod scans for usr/local/lib/nmos." >&2
    exit 1
}

grep -Fxq '*.sh text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for shell scripts." >&2
    exit 1
}

grep -Fxq '*.hook.chroot text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for chroot hooks." >&2
    exit 1
}

grep -Fxq '*.hook.binary text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for binary hooks." >&2
    exit 1
}

grep -Fxq '*.ps1 text eol=crlf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin CRLF endings for PowerShell scripts." >&2
    exit 1
}

grep -Fxq 'config/live-build/auto/* text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for live-build auto scripts." >&2
    exit 1
}

grep -Fxq 'config/live-build/includes.chroot/usr/local/bin/* text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for extensionless runtime launchers." >&2
    exit 1
}

grep -Fxq 'config/live-build/includes.chroot/etc/gdm3/PostLogin/* text eol=lf' "${GITATTRIBUTES}" || {
    echo ".gitattributes does not pin LF endings for GDM PostLogin hooks." >&2
    exit 1
}

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import os
import subprocess
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
tracked = subprocess.check_output(["git", "-C", str(root), "ls-files"], text=True).splitlines()
lf_patterns = (".sh", ".hook.chroot", ".hook.binary", ".py")
crlf_patterns = (".ps1",)
lf_violations: list[str] = []
crlf_violations: list[str] = []

for rel in tracked:
    path = root / rel
    if not path.is_file():
        continue
    data = path.read_bytes()
    if rel.endswith(lf_patterns) and b"\r\n" in data:
        lf_violations.append(rel)
    if rel.endswith(crlf_patterns) and b"\r\n" not in data:
        crlf_violations.append(rel)

if lf_violations:
    raise SystemExit("LF policy violation in: " + ", ".join(sorted(lf_violations)))
if crlf_violations:
    raise SystemExit("CRLF policy violation in: " + ", ".join(sorted(crlf_violations)))
PY

echo "Build hygiene checks passed"
