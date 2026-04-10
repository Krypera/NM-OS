from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path


class CryptoMountOps:
    def __init__(
        self,
        *,
        run_command: Callable[..., str],
        storage_error,
        mapper_name: str,
        mapper_path: Path,
        mount_point: Path,
        partlabel: str,
        default_timeout_seconds: int,
        partition_timeout_seconds: int,
        crypto_timeout_seconds: int,
        filesystem_timeout_seconds: int,
        fsck_check_timeout_seconds: int,
        fsck_repair_timeout_seconds: int,
        mount_timeout_seconds: int,
    ) -> None:
        self.run = run_command
        self.storage_error = storage_error
        self.mapper_name = mapper_name
        self.mapper_path = mapper_path
        self.mount_point = mount_point
        self.partlabel = partlabel
        self.default_timeout_seconds = default_timeout_seconds
        self.partition_timeout_seconds = partition_timeout_seconds
        self.crypto_timeout_seconds = crypto_timeout_seconds
        self.filesystem_timeout_seconds = filesystem_timeout_seconds
        self.fsck_check_timeout_seconds = fsck_check_timeout_seconds
        self.fsck_repair_timeout_seconds = fsck_repair_timeout_seconds
        self.mount_timeout_seconds = mount_timeout_seconds

    def is_mount_active(self, path: Path) -> bool:
        try:
            proc = subprocess.run(
                ["mountpoint", "-q", str(path)],
                check=False,
                timeout=self.mount_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise self.storage_error("mountpoint check timed out", reason="command_timeout") from exc
        return proc.returncode == 0

    def delete_partition(self, disk: str, partition_number: int) -> None:
        self.run(
            "sgdisk",
            "-d",
            str(partition_number),
            disk,
            timeout_seconds=self.partition_timeout_seconds,
            reason="backend_error",
        )
        self.run(
            "partprobe",
            disk,
            timeout_seconds=self.partition_timeout_seconds,
            reason="backend_error",
        )
        try:
            subprocess.run(
                ["udevadm", "settle"],
                check=False,
                timeout=self.partition_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return

    def create_partition(self, partition_plan: dict, *, wait_for_partition: Callable[[], str]) -> dict:
        partition_number = int(partition_plan["partition_number"])
        disk = str(partition_plan["device"])
        start_sector = int(partition_plan["start_sector"])
        self.run(
            "sgdisk",
            "-n",
            f"{partition_number}:{start_sector}:0",
            "-t",
            f"{partition_number}:8300",
            "-c",
            f"{partition_number}:{self.partlabel}",
            disk,
            timeout_seconds=self.partition_timeout_seconds,
            reason="backend_error",
        )
        self.run(
            "partprobe",
            disk,
            timeout_seconds=self.partition_timeout_seconds,
            reason="backend_error",
        )
        try:
            subprocess.run(
                ["udevadm", "settle"],
                check=False,
                timeout=self.partition_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            pass
        return {
            "path": wait_for_partition(),
            "device": disk,
            "partition_number": partition_number,
        }

    def format_luks(self, device: str, passphrase: str) -> None:
        self.run(
            "cryptsetup",
            "luksFormat",
            "--type",
            "luks2",
            "--batch-mode",
            device,
            "-",
            input_text=passphrase,
            timeout_seconds=self.crypto_timeout_seconds,
            reason="backend_error",
        )

    def open_mapper(self, device: str, passphrase: str) -> None:
        self.run(
            "cryptsetup",
            "open",
            device,
            self.mapper_name,
            "--key-file",
            "-",
            input_text=passphrase,
            timeout_seconds=self.crypto_timeout_seconds,
            reason="backend_error",
        )

    def close_mapper(self) -> None:
        self.run(
            "cryptsetup",
            "close",
            self.mapper_name,
            timeout_seconds=self.crypto_timeout_seconds,
            reason="backend_error",
        )

    def make_filesystem(self) -> None:
        self.run(
            "mkfs.ext4",
            "-F",
            "-L",
            "NMOS_DATA",
            str(self.mapper_path),
            timeout_seconds=self.filesystem_timeout_seconds,
            reason="backend_error",
        )

    def mount_mapper(self) -> None:
        self.mount_point.mkdir(parents=True, exist_ok=True)
        if not self.is_mount_active(self.mount_point):
            self.run(
                "mount",
                str(self.mapper_path),
                str(self.mount_point),
                timeout_seconds=self.mount_timeout_seconds,
                reason="backend_error",
            )

    def unmount_mapper(self) -> None:
        if self.is_mount_active(self.mount_point):
            self.run(
                "umount",
                str(self.mount_point),
                timeout_seconds=self.mount_timeout_seconds,
                reason="backend_error",
            )

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
                    ["umount", str(self.mount_point)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.mount_timeout_seconds,
                )
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                cleanup_errors.append(f"failed to unmount partial persistence mount: {exc}")

        if mapper_opened and self.mapper_path.exists():
            try:
                self.close_mapper()
            except (OSError, RuntimeError, ValueError) as exc:
                cleanup_errors.append(f"failed to close partially opened mapper: {exc}")

        if created_partition is not None:
            try:
                self.delete_partition(str(created_partition["device"]), int(created_partition["partition_number"]))
            except (OSError, RuntimeError, ValueError) as exc:
                cleanup_errors.append(f"failed to remove partially created partition: {exc}")
        return cleanup_errors

    def run_repair(self) -> None:
        try:
            precheck = subprocess.run(
                ["fsck.ext4", "-n", str(self.mapper_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.fsck_check_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise self.storage_error("fsck pre-check timed out", reason="command_timeout") from exc

        if precheck.returncode in {0}:
            return
        if precheck.returncode in {1, 2, 3, 4}:
            self.run(
                "fsck.ext4",
                "-y",
                str(self.mapper_path),
                timeout_seconds=self.fsck_repair_timeout_seconds,
                reason="backend_error",
            )
            return
        detail = (precheck.stderr or precheck.stdout or f"exit={precheck.returncode}").strip()
        raise self.storage_error(f"fsck pre-check failed: {detail}", reason="backend_error")
