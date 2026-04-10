from __future__ import annotations

import json
import os
from pathlib import Path


def ensure_runtime_state_path_safe(path: Path) -> None:
    if path.parent.is_symlink():
        raise OSError(f"runtime state directory must not be a symlink: {path.parent}")
    if path.exists() and path.is_symlink():
        raise OSError(f"runtime state path must not be a symlink: {path}")
    if path.exists() and not path.is_file():
        raise OSError(f"runtime state path must be a regular file: {path}")


def open_runtime_state_file(path: Path, mode: int) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags, mode)


def write_runtime_text(
    path: Path,
    content: str,
    *,
    mode: int = 0o644,
    owner_uid: int | None = None,
    owner_gid: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_runtime_state_path_safe(path)
    fd = open_runtime_state_file(path, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    if owner_uid is not None or owner_gid is not None:
        os.chown(path, owner_uid if owner_uid is not None else -1, owner_gid if owner_gid is not None else -1)


def write_runtime_json(
    path: Path,
    payload: dict,
    *,
    mode: int = 0o644,
    owner_uid: int | None = None,
    owner_gid: int | None = None,
) -> None:
    write_runtime_text(
        path,
        json.dumps(payload, indent=2),
        mode=mode,
        owner_uid=owner_uid,
        owner_gid=owner_gid,
    )
