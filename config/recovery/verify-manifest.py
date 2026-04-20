#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: verify-manifest.py <manifest> <signature> <keyring>", file=sys.stderr)
        return 2
    manifest_path = Path(argv[1])
    signature_path = Path(argv[2])
    keyring_path = Path(argv[3])
    for path in (manifest_path, signature_path, keyring_path):
        if not path.exists():
            print(f"missing required file: {path}", file=sys.stderr)
            return 1
    completed = subprocess.run(
        ["gpgv", "--keyring", str(keyring_path), str(signature_path), str(manifest_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        print(completed.stderr or completed.stdout or f"gpgv exit={completed.returncode}", file=sys.stderr)
        return 1
    print(f"verified manifest sha256={sha256(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
