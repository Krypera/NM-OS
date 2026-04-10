from __future__ import annotations

import subprocess
from pathlib import Path

from nmos_persistent_storage.disk_discovery import DiskDiscovery
from nmos_persistent_storage.mount_crypto_ops import CryptoMountOps
from nmos_persistent_storage.partition_planning import (
    ALIGNMENT_BYTES,
    MIN_CREATE_BYTES,
    SUPPORTED_PARTITION_LABELS,
    boot_disk_is_supported,
    partition_table_label_is_supported,
    plan_trailing_partition,
)
from nmos_persistent_storage.state_serialization import build_state_payload, dump_runtime_state

RUNTIME_DIR = Path("/run/nmos")
STATE_FILE = RUNTIME_DIR / "persistent-storage.json"
MAPPER_NAME = "nmos-persist"
MAPPER_PATH = Path("/dev/mapper") / MAPPER_NAME
MOUNT_POINT = Path("/live/persistence/nmos-data")
PARTLABEL = "NMOS_PERSIST"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 30
PARTITION_COMMAND_TIMEOUT_SECONDS = 60
CRYPTO_COMMAND_TIMEOUT_SECONDS = 180
FS_COMMAND_TIMEOUT_SECONDS = 180
FSCK_CHECK_TIMEOUT_SECONDS = 180
FSCK_REPAIR_TIMEOUT_SECONDS = 600
MOUNT_COMMAND_TIMEOUT_SECONDS = 30

REASON_BACKEND_ERROR = "backend_error"
REASON_INVALID_REQUEST = "invalid_request"
REASON_ALREADY_EXISTS = "already_exists"
REASON_MISSING_PARTITION = "missing_partition"
REASON_LOCKED = "locked"
REASON_TIMEOUT = "command_timeout"

__all__ = [
    "ALIGNMENT_BYTES",
    "MIN_CREATE_BYTES",
    "PARTLABEL",
    "PersistentStorageManager",
    "REASON_ALREADY_EXISTS",
    "REASON_BACKEND_ERROR",
    "REASON_INVALID_REQUEST",
    "REASON_LOCKED",
    "REASON_MISSING_PARTITION",
    "REASON_TIMEOUT",
    "STATE_FILE",
    "SUPPORTED_PARTITION_LABELS",
    "StorageError",
    "boot_disk_is_supported",
    "partition_table_label_is_supported",
    "plan_trailing_partition",
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
        self.discovery = DiskDiscovery(
            run_command=lambda *args, **kwargs: self.run(*args, **kwargs),
            storage_error=StorageError,
            partlabel=PARTLABEL,
            default_timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
            partition_timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
        )
        self.crypto_ops = CryptoMountOps(
            run_command=lambda *args, **kwargs: self.run(*args, **kwargs),
            storage_error=StorageError,
            mapper_name=MAPPER_NAME,
            mapper_path=MAPPER_PATH,
            mount_point=MOUNT_POINT,
            partlabel=PARTLABEL,
            default_timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
            partition_timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
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

    def locate_partition(self) -> str | None:
        return self.discovery.locate_partition()

    def describe_persistence(self) -> dict:
        return self.discovery.describe_persistence()

    def plan_new_partition(self) -> dict:
        return self.discovery.plan_new_partition()

    def create_partition(self) -> dict:
        return self.crypto_ops.create_partition(self.plan_new_partition(), wait_for_partition=self.discovery.wait_for_partition)

    def dump_state(self, state: dict) -> dict:
        return dump_runtime_state(STATE_FILE, state)

    def get_state(self, include_cached_error: bool = False) -> dict:
        try:
            details = self.describe_persistence()
        except StorageError as exc:
            details = {
                "created": False,
                "boot_device_supported": False,
                "can_create": False,
                "reason": exc.reason,
                "device": "",
                "detail_error": str(exc),
                "free_bytes": 0,
            }
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            details = {
                "created": False,
                "boot_device_supported": False,
                "can_create": False,
                "reason": REASON_BACKEND_ERROR,
                "device": "",
                "detail_error": str(exc),
                "free_bytes": 0,
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
        created_partition: dict | None = None
        mapper_opened = False
        mount_active = False
        include_cached_error = False
        try:
            if not passphrase:
                raise StorageError("passphrase is required", reason=REASON_INVALID_REQUEST)
            if self.locate_partition():
                raise StorageError("persistence partition already exists", reason=REASON_ALREADY_EXISTS)
            created_partition = self.create_partition()
            device = str(created_partition["path"])
            self.crypto_ops.format_luks(device, passphrase)
            self.crypto_ops.open_mapper(device, passphrase)
            mapper_opened = True
            self.crypto_ops.make_filesystem()
            self.crypto_ops.mount_mapper()
            mount_active = self.crypto_ops.is_mount_active(MOUNT_POINT)
            (MOUNT_POINT / ".nmos-persist").write_text("NM-OS persistence\n", encoding="utf-8")
            self.clear_last_error()
        except StorageError as exc:
            cleanup_errors = self.crypto_ops.cleanup_failed_create(
                created_partition=created_partition,
                mapper_opened=mapper_opened,
                mount_active=mount_active,
            )
            self.set_last_error(str(exc), reason=exc.reason)
            if cleanup_errors:
                self.last_error = f"{self.last_error}; cleanup: {'; '.join(cleanup_errors)}"
            include_cached_error = True
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            cleanup_errors = self.crypto_ops.cleanup_failed_create(
                created_partition=created_partition,
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
            device = self.locate_partition()
            if not device:
                raise StorageError("persistence partition not found", reason=REASON_MISSING_PARTITION)
            if not MAPPER_PATH.exists():
                self.crypto_ops.open_mapper(device, passphrase)
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
                raise StorageError("persistence volume must be unlocked before repair", reason=REASON_LOCKED)
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
                    remount_error = f"failed to remount persistence after repair: {exc}"
                    if self.last_error:
                        self.last_error = f"{self.last_error}; {remount_error}"
                    else:
                        self.last_error = remount_error
                    self.last_error_reason = REASON_BACKEND_ERROR
                    include_cached_error = True
            self.current_operation = "idle"
            self.busy = False
        return self.get_state(include_cached_error=include_cached_error)
