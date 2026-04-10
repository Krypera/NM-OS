from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

from nmos_persistent_storage.partition_planning import (
    boot_disk_is_supported,
    partition_table_label_is_supported,
    plan_trailing_partition,
)


class DiskDiscovery:
    def __init__(
        self,
        *,
        run_command: Callable[..., str],
        storage_error,
        partlabel: str,
        default_timeout_seconds: int,
        partition_timeout_seconds: int,
    ) -> None:
        self.run = run_command
        self.storage_error = storage_error
        self.partlabel = partlabel
        self.default_timeout_seconds = default_timeout_seconds
        self.partition_timeout_seconds = partition_timeout_seconds
        self._boot_partition: str | None = None
        self._boot_disk: str | None = None

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
                timeout_seconds=self.default_timeout_seconds,
                reason="backend_error",
            )
        )
        devices = data.get("blockdevices", [])
        if not devices:
            raise self.storage_error(f"lsblk returned no data for {device}")
        return devices[0]

    def get_boot_partition(self) -> str:
        if self._boot_partition is not None:
            return self._boot_partition

        source = self.run(
            "findmnt",
            "-no",
            "SOURCE",
            "/run/live/medium",
            timeout_seconds=self.default_timeout_seconds,
            reason="backend_error",
        )
        if not source.startswith("/dev/"):
            raise self.storage_error("live system is not running from a block device", reason="unsupported_boot_device")
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
            timeout_seconds=self.default_timeout_seconds,
            reason="backend_error",
        ).strip()
        disk = f"/dev/{parent}" if parent else boot_partition
        facts = self.lsblk_entry(disk, "PATH,TYPE,RM,HOTPLUG,TRAN")
        if facts.get("type") != "disk":
            raise self.storage_error("boot medium is not a disk device", reason="unsupported_boot_device")
        if not boot_disk_is_supported(
            facts.get("tran"),
            self.is_true(facts.get("rm")),
            self.is_true(facts.get("hotplug")),
        ):
            raise self.storage_error("boot medium is not a removable USB device", reason="unsupported_boot_device")
        self._boot_disk = disk
        return disk

    def get_boot_disk_facts(self) -> dict:
        disk = self.get_boot_disk()
        facts = self.lsblk_entry(disk, "PATH,TYPE,RM,HOTPLUG,TRAN,RO,SIZE")
        facts["device"] = facts.get("path") or disk
        return facts

    @staticmethod
    def extract_partition_number(device: str) -> int | None:
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
                    timeout_seconds=self.partition_timeout_seconds,
                    reason="unsupported_layout",
                )
            )
        except self.storage_error as exc:
            raise self.storage_error(f"unable to read boot USB partition table: {exc}", reason=exc.reason) from exc
        except (OSError, ValueError, TypeError) as exc:
            raise self.storage_error(f"unable to read boot USB partition table: {exc}", reason="unsupported_layout") from exc

        table = data.get("partitiontable", {})
        try:
            sector_size = int(
                table.get("sectorsize")
                or self.run(
                    "blockdev",
                    "--getss",
                    disk,
                    timeout_seconds=self.default_timeout_seconds,
                    reason="unsupported_layout",
                )
            )
        except (TypeError, ValueError) as exc:
            raise self.storage_error("invalid sector size in boot USB partition table", reason="unsupported_layout") from exc
        label = str(table.get("label", "")).lower()
        if not partition_table_label_is_supported(label):
            raise self.storage_error(f"unsupported boot USB partition table label: {label or 'unknown'}", reason="unsupported_layout")

        partitions = []
        for item in table.get("partitions", []) or []:
            node = item.get("node", "")
            try:
                start_sectors = int(item.get("start", 0))
                size_sectors = int(item.get("size", 0))
            except (TypeError, ValueError) as exc:
                raise self.storage_error("invalid boot USB partition offsets", reason="unsupported_layout") from exc
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
                    timeout_seconds=self.default_timeout_seconds,
                    reason="backend_error",
                )
            )
        except (TypeError, ValueError) as exc:
            raise self.storage_error("unable to read boot USB size", reason="backend_error") from exc

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
                timeout_seconds=self.default_timeout_seconds,
                reason="backend_error",
            ).strip()
        except self.storage_error:
            return False
        if not parent:
            return candidate == disk
        return f"/dev/{parent}" == disk

    def locate_partition(self) -> str | None:
        try:
            disk = self.get_boot_disk()
        except self.storage_error:
            return None
        for candidate in (f"/dev/disk/by-partlabel/{self.partlabel}", f"/dev/disk/by-label/{self.partlabel}"):
            if Path(candidate).exists():
                resolved = str(Path(candidate).resolve())
                if self.partition_belongs_to_disk(resolved, disk):
                    return resolved
        return None

    def describe_persistence(self) -> dict:
        try:
            facts = self.get_boot_disk_facts()
        except self.storage_error as exc:
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
        except self.storage_error as exc:
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
            raise self.storage_error("boot USB is read-only", reason="read_only")
        if self.locate_partition():
            raise self.storage_error("persistence partition already exists", reason="already_exists")

        layout = self.read_partition_table(device)
        plan = plan_trailing_partition(
            device_size_bytes=layout["device_size_bytes"],
            partitions=layout["partitions"],
        )
        if not plan["can_create"]:
            raise self.storage_error("not enough trailing free space on the boot USB for persistence", reason="no_free_space")

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
        raise self.storage_error("persistence partition was not created")
