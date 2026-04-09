from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path


RUNTIME_DIR = Path("/run/nmos")
STATE_FILE = RUNTIME_DIR / "persistent-storage.json"
MAPPER_NAME = "nmos-persist"
MAPPER_PATH = Path("/dev/mapper") / MAPPER_NAME
MOUNT_POINT = Path("/live/persistence/nmos-data")
PARTLABEL = "NMOS_PERSIST"
MIN_CREATE_BYTES = 1024 * 1024 * 1024
ALIGNMENT_BYTES = 1024 * 1024
SUPPORTED_PARTITION_LABELS = {"dos", "gpt"}


class StorageError(RuntimeError):
    def __init__(self, message: str, *, reason: str = "backend_error") -> None:
        super().__init__(message)
        self.reason = reason


def boot_disk_is_supported(transport: str | None, removable: bool, hotplug: bool) -> bool:
    return transport == "usb" or removable or hotplug


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
        self._boot_partition: str | None = None
        self._boot_disk: str | None = None
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, *args: str, input_text: str | None = None) -> str:
        proc = subprocess.run(
            args,
            check=True,
            text=True,
            input=input_text,
            capture_output=True,
        )
        return proc.stdout.strip()

    def is_true(self, value: object) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes"}

    def lsblk_entry(self, device: str, columns: str) -> dict:
        data = json.loads(self.run("lsblk", "-J", "-b", "-o", columns, device))
        devices = data.get("blockdevices", [])
        if not devices:
            raise StorageError(f"lsblk returned no data for {device}")
        return devices[0]

    def get_boot_partition(self) -> str:
        if self._boot_partition is not None:
            return self._boot_partition

        source = self.run("findmnt", "-no", "SOURCE", "/run/live/medium")
        if not source.startswith("/dev/"):
            raise StorageError("live system is not running from a block device", reason="unsupported_boot_device")
        self._boot_partition = str(Path(source).resolve()) if Path(source).exists() else source
        return self._boot_partition

    def get_boot_disk(self) -> str:
        if self._boot_disk is not None:
            return self._boot_disk

        boot_partition = self.get_boot_partition()
        parent = self.run("lsblk", "-ndo", "PKNAME", boot_partition).strip()
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
            data = json.loads(self.run("sfdisk", "--json", disk))
        except Exception as exc:
            raise StorageError(f"unable to read boot USB partition table: {exc}") from exc

        table = data.get("partitiontable", {})
        sector_size = int(table.get("sectorsize") or self.run("blockdev", "--getss", disk))
        label = str(table.get("label", "")).lower()
        if not partition_table_label_is_supported(label):
            raise StorageError(
                f"unsupported boot USB partition table label: {label or 'unknown'}",
                reason="unsupported_layout",
            )
        partitions = []
        for item in table.get("partitions", []) or []:
            node = item.get("node", "")
            start_sectors = int(item.get("start", 0))
            size_sectors = int(item.get("size", 0))
            partitions.append(
                {
                    "path": node,
                    "number": self.extract_partition_number(node),
                    "start_bytes": start_sectors * sector_size,
                    "size_bytes": size_sectors * sector_size,
                }
            )

        return {
            "device_size_bytes": int(self.run("blockdev", "--getsize64", disk)),
            "sector_size": sector_size,
            "label": label,
            "partitions": partitions,
        }

    def partition_belongs_to_disk(self, candidate: str, disk: str) -> bool:
        parent = self.run("lsblk", "-ndo", "PKNAME", candidate).strip()
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
                "boot_device_supported": exc.reason != "unsupported_boot_device",
                "can_create": False,
                "reason": exc.reason,
                "device": "",
                "detail_error": str(exc),
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
            }

        if self.is_true(facts.get("ro")):
            return {
                "created": False,
                "boot_device_supported": True,
                "can_create": False,
                "reason": "read_only",
                "device": device,
                "detail_error": "",
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
        self.run("sgdisk", "-d", str(partition_number), disk)
        self.run("partprobe", disk)
        subprocess.run(["udevadm", "settle"], check=False)

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
        )
        self.run("partprobe", disk)
        subprocess.run(["udevadm", "settle"], check=False)
        return {
            "path": self.wait_for_partition(),
            "device": disk,
            "partition_number": partition_number,
        }

    def dump_state(self, state: dict) -> dict:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state

    def get_state(self, include_cached_error: bool = False) -> dict:
        details = self.describe_persistence()
        detail_error = details.get("detail_error", "")
        last_error = detail_error
        if not detail_error and include_cached_error:
            last_error = self.last_error
        created = bool(details.get("created"))
        can_create = bool(details.get("can_create"))
        state = {
            "created": created,
            "unlocked": MAPPER_PATH.exists(),
            "healthy": (created or can_create) and not last_error,
            "busy": self.busy,
            "last_error": last_error,
            "boot_device_supported": bool(details.get("boot_device_supported")),
            "can_create": can_create,
            "reason": details.get("reason", "backend_error"),
            "device": details.get("device", ""),
        }
        return self.dump_state(state)

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
                subprocess.run(["umount", str(MOUNT_POINT)], check=True, capture_output=True, text=True)
            except Exception as exc:
                cleanup_errors.append(f"failed to unmount partial persistence mount: {exc}")

        if mapper_opened and MAPPER_PATH.exists():
            try:
                self.run("cryptsetup", "close", MAPPER_NAME)
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
        created_partition: dict | None = None
        mapper_opened = False
        mount_active = False
        try:
            if not passphrase:
                raise StorageError("passphrase is required", reason="invalid_request")
            if self.locate_partition():
                raise StorageError("persistence partition already exists", reason="already_exists")
            created_partition = self.create_partition()
            device = str(created_partition["path"])
            self.run("cryptsetup", "luksFormat", "--type", "luks2", "--batch-mode", device, "-", input_text=passphrase)
            self.run("cryptsetup", "open", device, MAPPER_NAME, "--key-file", "-", input_text=passphrase)
            mapper_opened = True
            self.run("mkfs.ext4", "-F", "-L", "NMOS_DATA", str(MAPPER_PATH))
            MOUNT_POINT.mkdir(parents=True, exist_ok=True)
            if subprocess.run(["mountpoint", "-q", str(MOUNT_POINT)], check=False).returncode != 0:
                self.run("mount", str(MAPPER_PATH), str(MOUNT_POINT))
                mount_active = True
            (MOUNT_POINT / ".nmos-persist").write_text("NM-OS persistence\n", encoding="utf-8")
            self.last_error = ""
        except Exception as exc:
            cleanup_errors = self.cleanup_failed_create(
                created_partition=created_partition,
                mapper_opened=mapper_opened,
                mount_active=mount_active,
            )
            self.last_error = str(exc)
            if cleanup_errors:
                self.last_error = f"{self.last_error}; cleanup: {'; '.join(cleanup_errors)}"
            return self.get_state(include_cached_error=True)
        finally:
            self.busy = False
        return self.get_state()

    def unlock(self, passphrase: str) -> dict:
        self.busy = True
        try:
            if not passphrase:
                raise StorageError("passphrase is required", reason="invalid_request")
            device = self.locate_partition()
            if not device:
                raise StorageError("persistence partition not found", reason="missing_partition")
            if not MAPPER_PATH.exists():
                self.run("cryptsetup", "open", device, MAPPER_NAME, "--key-file", "-", input_text=passphrase)
            MOUNT_POINT.mkdir(parents=True, exist_ok=True)
            if subprocess.run(["mountpoint", "-q", str(MOUNT_POINT)], check=False).returncode != 0:
                self.run("mount", str(MAPPER_PATH), str(MOUNT_POINT))
            self.last_error = ""
        except Exception as exc:
            self.last_error = str(exc)
            return self.get_state(include_cached_error=True)
        finally:
            self.busy = False
        return self.get_state()

    def lock(self) -> dict:
        self.busy = True
        try:
            subprocess.run(["umount", str(MOUNT_POINT)], check=False)
            if MAPPER_PATH.exists():
                self.run("cryptsetup", "close", MAPPER_NAME)
            self.last_error = ""
        except Exception as exc:
            self.last_error = str(exc)
            return self.get_state(include_cached_error=True)
        finally:
            self.busy = False
        return self.get_state()

    def repair(self) -> dict:
        self.busy = True
        try:
            if not MAPPER_PATH.exists():
                raise StorageError("persistence volume must be unlocked before repair", reason="locked")
            self.run("fsck.ext4", "-y", str(MAPPER_PATH))
            self.last_error = ""
        except Exception as exc:
            self.last_error = str(exc)
            return self.get_state(include_cached_error=True)
        finally:
            self.busy = False
        return self.get_state()
