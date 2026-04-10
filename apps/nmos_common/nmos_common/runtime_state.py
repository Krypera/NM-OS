from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path


def ensure_runtime_state_path_safe(path: Path) -> None:
    if path.parent.is_symlink():
        raise OSError(f"runtime state directory must not be a symlink: {path.parent}")
    if path.parent.exists() and not path.parent.is_dir():
        raise OSError(f"runtime state directory must be a real directory: {path.parent}")
    if path.is_symlink():
        raise OSError(f"runtime state path must not be a symlink: {path}")
    if path.exists() and not path.is_file():
        raise OSError(f"runtime state path must be a regular file: {path}")


def _open_runtime_state_readonly(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags)


def _directory_fsync(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    with suppress(OSError):
        fd = os.open(directory, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _resolve_ownership(path: Path, owner_uid: int | None, owner_gid: int | None) -> tuple[int | None, int | None]:
    if owner_uid is not None and owner_gid is not None:
        return owner_uid, owner_gid
    with suppress(OSError):
        stat_result = path.stat(follow_symlinks=False)
        if owner_uid is None:
            owner_uid = stat_result.st_uid
        if owner_gid is None:
            owner_gid = stat_result.st_gid
    return owner_uid, owner_gid


def _apply_permissions(fd: int, temp_path: Path, mode: int) -> None:
    fchmod = getattr(os, "fchmod", None)
    if fchmod is not None:
        fchmod(fd, mode)
        return
    os.chmod(temp_path, mode)


def _apply_ownership(fd: int, temp_path: Path, owner_uid: int | None, owner_gid: int | None) -> None:
    if owner_uid is None and owner_gid is None:
        return
    normalized_uid = owner_uid if owner_uid is not None else -1
    normalized_gid = owner_gid if owner_gid is not None else -1
    fchown = getattr(os, "fchown", None)
    if fchown is not None:
        fchown(fd, normalized_uid, normalized_gid)
        return
    chown = getattr(os, "chown", None)
    if chown is not None:
        chown(temp_path, normalized_uid, normalized_gid)


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
    owner_uid, owner_gid = _resolve_ownership(path, owner_uid, owner_gid)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        _apply_permissions(fd, temp_path, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            _apply_ownership(handle.fileno(), temp_path, owner_uid, owner_gid)
        os.replace(temp_path, path)
        _directory_fsync(path.parent)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def read_runtime_text(path: Path) -> str:
    ensure_runtime_state_path_safe(path)
    fd = _open_runtime_state_readonly(path)
    with os.fdopen(fd, encoding="utf-8") as handle:
        return handle.read()


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
