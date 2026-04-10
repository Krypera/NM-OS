from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from nmos_common.runtime_state import write_runtime_json


RUNTIME_DIR = Path("/run/nmos")
STATE_FILE = RUNTIME_DIR / "persistent-storage.json"
MAPPER_NAME = "nmos-persist"
MAPPER_PATH = Path("/dev/mapper") / MAPPER_NAME
MOUNT_POINT = Path("/live/persistence/nmos-data")
PARTLABEL = "NMOS_PERSIST"
MIN_CREATE_BYTES = 1024 * 1024 * 1024
ALIGNMENT_BYTES = 1024 * 1024
SUPPORTED_PARTITION_LABELS = {"gpt"}
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


class StorageError(RuntimeError):
    def __init__(self, message: str, *, reason: str = REASON_BACKEND_ERROR) -> None:
        super().__init__(message)
        self.reason = reason


def boot_disk_is_supported(transport: str | None, removable: bool, hotplug: bool) -> bool:
    del hotplug
    return transport == "usb" or removable


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0:
        return value
    remainder = value % alignment
    if remainder == 0:
        return value
    return value + alignment - remainder


def next_partition_number(partitions: list[dict]) -> int:
    numbers = [int(partition.get("number", 0)) for partition in partitions if partition.get("number")]
    return max(numbers, default=0) + 1


def partition_table_label_is_supported(label: str | None) -> bool:
    return str(label or "").lower() in SUPPORTED_PARTITION_LABELS


def plan_trailing_partition(
    *,
    device_size_bytes: int,
    partitions: list[dict],
    minimum_free_bytes: int = MIN_CREATE_BYTES,
    alignment_bytes: int = ALIGNMENT_BYTES,
) -> dict:
    last_end = 0
    for partition in partitions:
        start = int(partition.get("start_bytes", 0))
        size = int(partition.get("size_bytes", 0))
        last_end = max(last_end, start + size)

    start_bytes = max(alignment_bytes, align_up(last_end, alignment_bytes))
    free_bytes = max(0, device_size_bytes - start_bytes)
    return {
        "partition_number": next_partition_number(partitions),
        "start_bytes": start_bytes,
        "free_bytes": free_bytes,
        "can_create": free_bytes >= minimum_free_bytes,
        "reason": "ready" if free_bytes >= minimum_free_bytes else "no_free_space",
    }


class PersistentStorageManager:
    def __init__(self) -> None:
        self.busy = False
        self.last_error = ""
        self.last_error_reason = REASON_BACKEND_ERROR
        self.current_operation = "idle"
        self._boot_partition: str | None = None
        self._boot_disk: str | None = None
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

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

    def is_mount_active(self, path: Path) -> bool:
        try:
            proc = subprocess.run(
                ["mountpoint", "-q", str(path)],
                check=False,
                timeout=MOUNT_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise StorageError("mountpoint check timed out", reason=REASON_TIMEOUT) from exc
        return proc.returncode == 0

    def is_true(self, value: object) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes"}

    def lsblk_entry(self, device: str, columns: str) -> dict:
        data = json.loads(
            self.run(
                "lsblk",
                "-J",
                "-b",
                "-o",
                columns,
                device,
                timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
                reason=REASON_BACKEND_ERROR,
            )
        )
        devices = data.get("blockdevices", [])
        if not devices:
            raise StorageError(f"lsblk returned no data for {device}")
        return devices[0]

    def get_boot_partition(self) -> str:
        if self._boot_partition is not None:
            return self._boot_partition

        source = self.run(
            "findmnt",
            "-no",
            "SOURCE",
            "/run/live/medium",
            timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        )
        if not source.startswith("/dev/"):
            raise StorageError("live system is not running from a block device", reason="unsupported_boot_device")
        self._boot_partition = str(Path(source).resolve()) if Path(source).exists() else source
        return self._boot_partition

    def get_boot_disk(self) -> str:
        if self._boot_disk is not None:
            return self._boot_disk

        boot_partition = self.get_boot_partition()
        parent = self.run(
            "lsblk",
            "-ndo",
            "PKNAME",
            boot_partition,
            timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        ).strip()
        disk = f"/dev/{parent}" if parent else boot_partition
        facts = self.lsblk_entry(disk, "PATH,TYPE,RM,HOTPLUG,TRAN")
        if facts.get("type") != "disk":
            raise StorageError("boot medium is not a disk device", reason="unsupported_boot_device")
        if not boot_disk_is_supported(
            facts.get("tran"),
            self.is_true(facts.get("rm")),
            self.is_true(facts.get("hotplug")),
        ):
            raise StorageError("boot medium is not a removable USB device", reason="unsupported_boot_device")
        self._boot_disk = disk
        return disk

    def get_boot_disk_facts(self) -> dict:
        disk = self.get_boot_disk()
        facts = self.lsblk_entry(disk, "PATH,TYPE,RM,HOTPLUG,TRAN,RO,SIZE")
        facts["device"] = facts.get("path") or disk
        return facts

    def extract_partition_number(self, device: str) -> int | None:
        match = re.search(r"(?:p)?(\d+)$", device)
        if match is None:
            return None
        return int(match.group(1))

    def read_partition_table(self, disk: str) -> dict:
        try:
            data = json.loads(
                self.run(
                    "sfdisk",
                    "--json",
                    disk,
                    timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
                    reason="unsupported_layout",
                )
            )
        except StorageError as exc:
            raise StorageError(f"unable to read boot USB partition table: {exc}", reason=exc.reason) from exc
        except Exception as exc:
            raise StorageError(f"unable to read boot USB partition table: {exc}", reason="unsupported_layout") from exc

        table = data.get("partitiontable", {})
        try:
            sector_size = int(
                table.get("sectorsize")
                or self.run(
                    "blockdev",
                    "--getss",
                    disk,
                    timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
                    reason="unsupported_layout",
                )
            )
        except (TypeError, ValueError) as exc:
            raise StorageError("invalid sector size in boot USB partition table", reason="unsupported_layout") from exc
        label = str(table.get("label", "")).lower()
        if not partition_table_label_is_supported(label):
            raise StorageError(
                f"unsupported boot USB partition table label: {label or 'unknown'}",
                reason="unsupported_layout",
            )
        partitions = []
        for item in table.get("partitions", []) or []:
            node = item.get("node", "")
            try:
                start_sectors = int(item.get("start", 0))
                size_sectors = int(item.get("size", 0))
            except (TypeError, ValueError) as exc:
                raise StorageError("invalid boot USB partition offsets", reason="unsupported_layout") from exc
            partitions.append(
                {
                    "path": node,
                    "number": self.extract_partition_number(node),
                    "start_bytes": start_sectors * sector_size,
                    "size_bytes": size_sectors * sector_size,
                }
            )

        try:
            device_size = int(
                self.run(
                    "blockdev",
                    "--getsize64",
                    disk,
                    timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            )
        except (TypeError, ValueError) as exc:
            raise StorageError("unable to read boot USB size", reason=REASON_BACKEND_ERROR) from exc

        return {
            "device_size_bytes": device_size,
            "sector_size": sector_size,
            "label": label,
            "partitions": partitions,
        }

    def partition_belongs_to_disk(self, candidate: str, disk: str) -> bool:
        try:
            parent = self.run(
                "lsblk",
                "-ndo",
                "PKNAME",
                candidate,
                timeout_seconds=DEFAULT_COMMAND_TIMEOUT_SECONDS,
                reason=REASON_BACKEND_ERROR,
            ).strip()
        except Exception:
            return False
        if not parent:
            return candidate == disk
        return f"/dev/{parent}" == disk

    def locate_partition(self) -> str | None:
        try:
            disk = self.get_boot_disk()
        except StorageError:
            return None
        for candidate in (
            f"/dev/disk/by-partlabel/{PARTLABEL}",
            f"/dev/disk/by-label/{PARTLABEL}",
        ):
            if Path(candidate).exists():
                resolved = str(Path(candidate).resolve())
                if self.partition_belongs_to_disk(resolved, disk):
                    return resolved
        return None

    def describe_persistence(self) -> dict:
        try:
            facts = self.get_boot_disk_facts()
        except StorageError as exc:
            return {
                "created": False,
                "boot_device_supported": False,
                "can_create": False,
                "reason": exc.reason,
                "device": "",
                "detail_error": str(exc),
                "free_bytes": 0,
            }

        device = str(facts["device"])
        existing = self.locate_partition()
        if existing:
            return {
                "created": True,
                "boot_device_supported": True,
                "can_create": False,
                "reason": "already_exists",
                "device": device,
                "detail_error": "",
                "free_bytes": 0,
            }

        if self.is_true(facts.get("ro")):
            return {
                "created": False,
                "boot_device_supported": True,
                "can_create": False,
                "reason": "read_only",
                "device": device,
                "detail_error": "",
                "free_bytes": 0,
            }

        try:
            layout = self.read_partition_table(device)
            plan = plan_trailing_partition(
                device_size_bytes=layout["device_size_bytes"],
                partitions=layout["partitions"],
            )
        except StorageError as exc:
            return {
                "created": False,
                "boot_device_supported": True,
                "can_create": False,
                "reason": exc.reason,
                "device": device,
                "detail_error": str(exc),
                "free_bytes": 0,
            }

        return {
            "created": False,
            "boot_device_supported": True,
            "can_create": plan["can_create"],
            "reason": plan["reason"],
            "device": device,
            "detail_error": "",
            "free_bytes": plan["free_bytes"],
        }

    def plan_new_partition(self) -> dict:
        facts = self.get_boot_disk_facts()
        device = str(facts["device"])
        if self.is_true(facts.get("ro")):
            raise StorageError("boot USB is read-only", reason="read_only")

        if self.locate_partition():
            raise StorageError("persistence partition already exists", reason="already_exists")

        layout = self.read_partition_table(device)
        plan = plan_trailing_partition(
            device_size_bytes=layout["device_size_bytes"],
            partitions=layout["partitions"],
        )
        if not plan["can_create"]:
            raise StorageError(
                "not enough trailing free space on the boot USB for persistence",
                reason="no_free_space",
            )

        start_sector = plan["start_bytes"] // layout["sector_size"]
        return {
            "device": device,
            "partition_number": plan["partition_number"],
            "start_sector": start_sector,
            "free_bytes": plan["free_bytes"],
        }

    def wait_for_partition(self) -> str:
        deadline = time.time() + 15
        while time.time() < deadline:
            candidate = self.locate_partition()
            if candidate:
                return candidate
            time.sleep(1)
        raise StorageError("persistence partition was not created")

    def delete_partition(self, disk: str, partition_number: int) -> None:
        self.run(
            "sgdisk",
            "-d",
            str(partition_number),
            disk,
            timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        )
        self.run(
            "partprobe",
            disk,
            timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        )
        try:
            subprocess.run(
                ["udevadm", "settle"],
                check=False,
                timeout=PARTITION_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            pass

    def create_partition(self) -> dict:
        plan = self.plan_new_partition()
        partition_number = int(plan["partition_number"])
        disk = str(plan["device"])
        start_sector = int(plan["start_sector"])

        self.run(
            "sgdisk",
            "-n",
            f"{partition_number}:{start_sector}:0",
            "-t",
            f"{partition_number}:8300",
            "-c",
            f"{partition_number}:{PARTLABEL}",
            disk,
            timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        )
        self.run(
            "partprobe",
            disk,
            timeout_seconds=PARTITION_COMMAND_TIMEOUT_SECONDS,
            reason=REASON_BACKEND_ERROR,
        )
        try:
            subprocess.run(
                ["udevadm", "settle"],
                check=False,
                timeout=PARTITION_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            pass
        return {
            "path": self.wait_for_partition(),
            "device": disk,
            "partition_number": partition_number,
        }

    def dump_state(self, state: dict) -> dict:
        write_runtime_json(STATE_FILE, state, mode=0o640)
        return state

    def get_state(self, include_cached_error: bool = False) -> dict:
        try:
            details = self.describe_persistence()
        except Exception as exc:
            details = {
                "created": False,
                "boot_device_supported": False,
                "can_create": False,
                "reason": "backend_error",
                "device": "",
                "detail_error": str(exc),
                "free_bytes": 0,
            }
        detail_error = details.get("detail_error", "")
        last_error = detail_error
        reason = str(details.get("reason", REASON_BACKEND_ERROR))
        if not detail_error and include_cached_error and self.last_error:
            last_error = self.last_error
            reason = self.last_error_reason
        mapper_open = MAPPER_PATH.exists()
        mounted = False
        if mapper_open:
            try:
                mounted = self.is_mount_active(MOUNT_POINT)
            except StorageError as exc:
                if not last_error:
                    last_error = str(exc)
                    reason = exc.reason
        created = bool(details.get("created"))
        can_create = bool(details.get("can_create"))
        state = {
            "created": created,
            "unlocked": mapper_open,
            "mapper_open": mapper_open,
            "mounted": mounted,
            "healthy": (created or can_create) and not last_error,
            "busy": self.busy,
            "operation": self.current_operation if self.busy else "idle",
            "last_error": last_error,
            "boot_device_supported": bool(details.get("boot_device_supported")),
            "can_create": can_create,
            "reason": reason,
            "device": details.get("device", ""),
            "free_bytes": int(details.get("free_bytes", 0) or 0),
        }
        try:
            return self.dump_state(state)
        except OSError as exc:
            state["last_error"] = state["last_error"] or f"state_write_failed: {exc}"
            state["healthy"] = False
            return state

    def cleanup_failed_create(
        self,
        *,
        created_partition: dict | None,
        mapper_opened: bool,
        mount_active: bool,
    ) -> list[str]:
        cleanup_errors: list[str] = []

        if mount_active:
            try:
                subprocess.run(
                    ["umount", str(MOUNT_POINT)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=MOUNT_COMMAND_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                cleanup_errors.append(f"failed to unmount partial persistence mount: {exc}")

        if mapper_opened and MAPPER_PATH.exists():
            try:
                self.run(
                    "cryptsetup",
                    "close",
                    MAPPER_NAME,
                    timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            except Exception as exc:
                cleanup_errors.append(f"failed to close partially opened mapper: {exc}")

        if created_partition is not None:
            try:
                self.delete_partition(str(created_partition["device"]), int(created_partition["partition_number"]))
            except Exception as exc:
                cleanup_errors.append(f"failed to remove partially created partition: {exc}")

        return cleanup_errors

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
            self.run(
                "cryptsetup",
                "luksFormat",
                "--type",
                "luks2",
                "--batch-mode",
                device,
                "-",
                input_text=passphrase,
                timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
                reason=REASON_BACKEND_ERROR,
            )
            self.run(
                "cryptsetup",
                "open",
                device,
                MAPPER_NAME,
                "--key-file",
                "-",
                input_text=passphrase,
                timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
                reason=REASON_BACKEND_ERROR,
            )
            mapper_opened = True
            self.run(
                "mkfs.ext4",
                "-F",
                "-L",
                "NMOS_DATA",
                str(MAPPER_PATH),
                timeout_seconds=FS_COMMAND_TIMEOUT_SECONDS,
                reason=REASON_BACKEND_ERROR,
            )
            MOUNT_POINT.mkdir(parents=True, exist_ok=True)
            if not self.is_mount_active(MOUNT_POINT):
                self.run(
                    "mount",
                    str(MAPPER_PATH),
                    str(MOUNT_POINT),
                    timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
                mount_active = True
            (MOUNT_POINT / ".nmos-persist").write_text("NM-OS persistence\n", encoding="utf-8")
            self.clear_last_error()
        except StorageError as exc:
            cleanup_errors = self.cleanup_failed_create(
                created_partition=created_partition,
                mapper_opened=mapper_opened,
                mount_active=mount_active,
            )
            self.set_last_error(str(exc), reason=exc.reason)
            if cleanup_errors:
                self.last_error = f"{self.last_error}; cleanup: {'; '.join(cleanup_errors)}"
            include_cached_error = True
        except Exception as exc:
            cleanup_errors = self.cleanup_failed_create(
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
                self.run(
                    "cryptsetup",
                    "open",
                    device,
                    MAPPER_NAME,
                    "--key-file",
                    "-",
                    input_text=passphrase,
                    timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            MOUNT_POINT.mkdir(parents=True, exist_ok=True)
            if not self.is_mount_active(MOUNT_POINT):
                self.run(
                    "mount",
                    str(MAPPER_PATH),
                    str(MOUNT_POINT),
                    timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except Exception as exc:
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
            if self.is_mount_active(MOUNT_POINT):
                self.run(
                    "umount",
                    str(MOUNT_POINT),
                    timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            if MAPPER_PATH.exists():
                self.run(
                    "cryptsetup",
                    "close",
                    MAPPER_NAME,
                    timeout_seconds=CRYPTO_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except Exception as exc:
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
            if self.is_mount_active(MOUNT_POINT):
                self.run(
                    "umount",
                    str(MOUNT_POINT),
                    timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
                    reason=REASON_BACKEND_ERROR,
                )
                remount_required = True
            try:
                precheck = subprocess.run(
                    ["fsck.ext4", "-n", str(MAPPER_PATH)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=FSCK_CHECK_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                raise StorageError("fsck pre-check timed out", reason=REASON_TIMEOUT) from exc

            if precheck.returncode not in {0}:
                if precheck.returncode in {1, 2, 3, 4}:
                    self.run(
                        "fsck.ext4",
                        "-y",
                        str(MAPPER_PATH),
                        timeout_seconds=FSCK_REPAIR_TIMEOUT_SECONDS,
                        reason=REASON_BACKEND_ERROR,
                    )
                else:
                    detail = (precheck.stderr or precheck.stdout or f"exit={precheck.returncode}").strip()
                    raise StorageError(f"fsck pre-check failed: {detail}", reason=REASON_BACKEND_ERROR)
            self.clear_last_error()
        except StorageError as exc:
            self.set_last_error(str(exc), reason=exc.reason)
            include_cached_error = True
        except Exception as exc:
            self.set_last_error(str(exc), reason=REASON_BACKEND_ERROR)
            include_cached_error = True
        finally:
            if remount_required and MAPPER_PATH.exists():
                try:
                    if not self.is_mount_active(MOUNT_POINT):
                        self.run(
                            "mount",
                            str(MAPPER_PATH),
                            str(MOUNT_POINT),
                            timeout_seconds=MOUNT_COMMAND_TIMEOUT_SECONDS,
                            reason=REASON_BACKEND_ERROR,
                        )
                except Exception as exc:
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
