from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nmos_persistent_storage.mount_crypto_ops import CryptoMountOps
from nmos_persistent_storage.state_serialization import build_state_payload, dump_runtime_state

RUNTIME_DIR = Path("/run/nmos")
STATE_FILE = RUNTIME_DIR / "persistent-storage.json"
STORAGE_ROOT = Path("/var/lib/nmos/storage")
VAULT_IMAGE_PATH = STORAGE_ROOT / "vault.img"
MAPPER_NAME = "nmos-vault"
MAPPER_PATH = Path("/dev/mapper") / MAPPER_NAME
MOUNT_POINT = STORAGE_ROOT / "mnt"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 30
CRYPTO_COMMAND_TIMEOUT_SECONDS = 180
FS_COMMAND_TIMEOUT_SECONDS = 180
FSCK_CHECK_TIMEOUT_SECONDS = 180
FSCK_REPAIR_TIMEOUT_SECONDS = 600
MOUNT_COMMAND_TIMEOUT_SECONDS = 30
DEFAULT_VAULT_SIZE_BYTES = 8 * 1024 * 1024 * 1024

REASON_BACKEND_ERROR = "backend_error"
REASON_INVALID_REQUEST = "invalid_request"
REASON_ALREADY_EXISTS = "already_exists"
REASON_MISSING_VAULT = "missing_vault"
REASON_LOCKED = "locked"
REASON_NO_SPACE = "no_space"
REASON_TIMEOUT = "command_timeout"

__all__ = [
    "DEFAULT_VAULT_SIZE_BYTES",
    "PersistentStorageManager",
    "REASON_ALREADY_EXISTS",
    "REASON_BACKEND_ERROR",
    "REASON_INVALID_REQUEST",
    "REASON_LOCKED",
    "REASON_MISSING_VAULT",
    "REASON_NO_SPACE",
    "REASON_TIMEOUT",
    "STATE_FILE",
    "StorageError",
]


class StorageError(RuntimeError):
    def __init__(self, message: str, *, reason: str = REASON_BACKEND_ERROR) -> None:
        super().__init__(message)
        self.reason = reason


class PersistentStorageManager:
    def __init__(self) -> None:
        self.busy = False
        self.last_error = ""
        self.last_error_reason = REASON_BACKEND_ERROR
        self.current_operation = "idle"
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.crypto_ops = CryptoMountOps(
            run_command=lambda *args, **kwargs: self.run(*args, **kwargs),
            storage_error=StorageError,
            mapper_name=MAPPER_NAME,
            mapper_path=MAPPER_PATH,
            image_path=VAULT_IMAGE_PATH,
            mount_point=MOUNT_POINT,
            crypto_timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
            filesystem_timeout_seconds=FS_COMMAND_TIMEOUT_SECONDS,
            fsck_check_timeout_seconds=FSCK_CHECK_TIMEOUT_SECONDS,
            fsck_repair_timeout_seconds=FSCK_REPAIR_TIMEOUT_SECONDS,
            mount_timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
        )

    def set_last_error(self, message: str, *, reason: str = REASON_BACKEND_ERROR) -> None:
        self.last_error = message
        self.last_error_reason = reason

    def clear_last_error(self) -> None:
        self.last_error = ""
        self.last_error_reason = REASON_BACKEND_ERROR

    def run(
        self,
        *args: str,
        input_text: str | None = None,
        timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        reason: str = REASON_BACKEND_ERROR,
    ) -> str:
        try:
            proc = subprocess.run(
                args,
                check=True,
                text=True,
                input=input_text,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            command = " ".join(args)
            raise StorageError(f"command timed out ({command})", reason=REASON_TIMEOUT) from exc
        except subprocess.CalledProcessError as exc:
            stderr = str(exc.stderr or "").strip()
            stdout = str(exc.stdout or "").strip()
            detail = stderr or stdout or str(exc)
            command = " ".join(args)
            raise StorageError(f"command failed ({command}): {detail}", reason=reason) from exc
        return proc.stdout.strip()

    def _disk_usage(self):
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(STORAGE_ROOT)

    def describe_vault(self) -> dict:
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        if VAULT_IMAGE_PATH.exists():
            return {
                "created": True,
                "can_create": False,
                "reason": REASON_ALREADY_EXISTS,
                "path": str(VAULT_IMAGE_PATH),
                "detail_error": "",
                "free_bytes": self._disk_usage().free,
                "file_bytes": VAULT_IMAGE_PATH.stat().st_size,
            }

        usage = self._disk_usage()
        can_create = usage.free >= DEFAULT_VAULT_SIZE_BYTES
        return {
            "created": False,
            "can_create": can_create,
            "reason": "ready" if can_create else REASON_NO_SPACE,
            "path": str(VAULT_IMAGE_PATH),
            "detail_error": "",
            "free_bytes": usage.free,
            "file_bytes": 0,
        }

    def dump_state(self, state: dict) -> dict:
        return dump_runtime_state(STATE_FILE, state)

    def get_state(self, include_cached_error: bool = False) -> dict:
        try:
            details = self.describe_vault()
        except (OSError, RuntimeError, ValueError, TypeError, shutil.Error) as exc:
            details = {
                "created": False,
                "can_create": False,
                "reason": REASON_BACKEND_ERROR,
                "path": str(VAULT_IMAGE_PATH),
                "detail_error": str(exc),
                "free_bytes": 0,
                "file_bytes": 0,
            }
        mapper_open = MAPPER_PATH.exists()
        mounted = False
        if mapper_open:
            try:
                mounted = self.crypto_ops.is_mount_active(MOUNT_POINT)
            except StorageError as exc:
                details["detail_error"] = details.get("detail_error", "") or str(exc)
                details["reason"] = details.get("reason", REASON_BACKEND_ERROR) or exc.reason
        state = build_state_payload(
            details=details,
            mapper_open=mapper_open,
            mounted=mounted,
            busy=self.busy,
            operation=self.current_operation,
            cached_error=self.last_error,
            cached_error_reason=self.last_error_reason,
            include_cached_error=include_cached_error,
        )
        try:
            return self.dump_state(state)
        except OSError as exc:
            state["last_error"] = state["last_error"] or f"state_write_failed: {exc}"
            state["healthy"] = False
            return state

    def create(self, passphrase: str) -> dict:
        self.busy = True
        self.current_operation = "create"
        image_created = False
        mapper_opened = False
        mount_active = False
        include_cached_error = False
        try:
            if not passphrase:
                raise StorageError("passphrase is required", reason=REASON_INVALID_REQUEST)
            if VAULT_IMAGE_PATH.exists():
                raise StorageError("encrypted vault already exists", reason=REASON_ALREADY_EXISTS)
            details = self.describe_vault()
            if not details["can_create"]:
                raise StorageError("not enough free space for encrypted vault", reason=REASON_NO_SPACE)
            self.crypto_ops.create_image_file(DEFAULT_VAULT_SIZE_BYTES)
            image_created = True
            self.crypto_ops.format_luks(passphrase)
            self.crypto_ops.open_mapper(passphrase)
            mapper_opened = True
            self.crypto_ops.make_filesystem()
            self.crypto_ops.mount_mapper()
            mount_active = self.crypto_ops.is_mount_active(MOUNT_POINT)
            (MOUNT_POINT / ".nmos-vault").write_text("NM-OS encrypted vault\n", encoding="utf-8")
            self.clear_last_error()
        except StorageError as exc:
            cleanup_errors = self.crypto_ops.cleanup_failed_create(
                image_created=image_created,
                mapper_opened=mapper_opened,
                mount_active=mount_active,
            )
            self.set_last_error(str(exc), reason=exc.reason)
            if cleanup_errors:
                self.last_error = f"{self.last_error}; cleanup: {'; '.join(cleanup_errors)}"
            include_cached_error = True
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            cleanup_errors = self.crypto_ops.cleanup_failed_create(
                image_created=image_created,
                mapper_opened=mapper_opened,
                mount_active=mount_active,
            )
            self.set_last_error(str(exc), reason=REASON_BACKEND_ERROR)
            if cleanup_errors:
                self.last_error = f"{self.last_error}; cleanup: {'; '.join(cleanup_errors)}"
            include_cached_error = True
        finally:
            self.current_operation = "idle"
            self.busy = False
        return self.get_state(include_cached_error=include_cached_error)

    def unlock(self, passphrase: str) -> dict:
        self.busy = True
        self.current_operation = "unlock"
        include_cached_error = False
        try:
            if not passphrase:
                raise StorageError("passphrase is required", reason=REASON_INVALID_REQUEST)
            if not VAULT_IMAGE_PATH.exists():
                raise StorageError("encrypted vault not found", reason=REASON_MISSING_VAULT)
            if not MAPPER_PATH.exists():
                self.crypto_ops.open_mapper(passphrase)
            self.crypto_ops.mount_mapper()
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            self.set_last_error(str(exc), reason=REASON_BACKEND_ERROR)
            include_cached_error = True
        finally:
            self.current_operation = "idle"
            self.busy = False
        return self.get_state(include_cached_error=include_cached_error)

    def lock(self) -> dict:
        self.busy = True
        self.current_operation = "lock"
        include_cached_error = False
        try:
            self.crypto_ops.unmount_mapper()
            if MAPPER_PATH.exists():
                self.crypto_ops.close_mapper()
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            self.set_last_error(str(exc), reason=REASON_BACKEND_ERROR)
            include_cached_error = True
        finally:
            self.current_operation = "idle"
            self.busy = False
        return self.get_state(include_cached_error=include_cached_error)

    def repair(self) -> dict:
        self.busy = True
        self.current_operation = "repair"
        include_cached_error = False
        remount_required = False
        try:
            if not MAPPER_PATH.exists():
                raise StorageError("encrypted vault must be unlocked before repair", reason=REASON_LOCKED)
            if self.crypto_ops.is_mount_active(MOUNT_POINT):
                self.crypto_ops.unmount_mapper()
                remount_required = True
            self.crypto_ops.run_repair()
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            self.set_last_error(str(exc), reason=REASON_BACKEND_ERROR)
            include_cached_error = True
        finally:
            if remount_required and MAPPER_PATH.exists():
                try:
                    self.crypto_ops.mount_mapper()
                except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
                    remount_error = f"failed to remount encrypted vault after repair: {exc}"
                    if self.last_error:
                        self.last_error = f"{self.last_error}; {remount_error}"
                    else:
                        self.last_error = remount_error
                    self.last_error_reason = REASON_BACKEND_ERROR
                    include_cached_error = True
            self.current_operation = "idle"
            self.busy = False
        return self.get_state(include_cached_error=include_cached_error)
