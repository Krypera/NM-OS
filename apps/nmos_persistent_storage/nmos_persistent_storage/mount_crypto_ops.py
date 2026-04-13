from __future__ import annotations

import subprocess
from pathlib import Path


class CryptoMountOps:
    def __init__(
        self,
        *,
        run_command,
        storage_error,
        mapper_name: str,
        mapper_path: Path,
        image_path: Path,
        mount_point: Path,
        crypto_timeout_seconds: int,
        filesystem_timeout_seconds: int,
        fsck_check_timeout_seconds: int,
        fsck_repair_timeout_seconds: int,
        mount_timeout_seconds: int,
        luks_pbkdf: str,
        luks_iter_time_ms: int,
        luks_memory_kib: int,
        luks_parallel: int,
    ) -> None:
        self.run = run_command
        self.storage_error = storage_error
        self.mapper_name = mapper_name
        self.mapper_path = mapper_path
        self.image_path = image_path
        self.mount_point = mount_point
        self.crypto_timeout_seconds = crypto_timeout_seconds
        self.filesystem_timeout_seconds = filesystem_timeout_seconds
        self.fsck_check_timeout_seconds = fsck_check_timeout_seconds
        self.fsck_repair_timeout_seconds = fsck_repair_timeout_seconds
        self.mount_timeout_seconds = mount_timeout_seconds
        self.luks_pbkdf = luks_pbkdf
        self.luks_iter_time_ms = max(500, int(luks_iter_time_ms))
        self.luks_memory_kib = max(65536, int(luks_memory_kib))
        self.luks_parallel = max(1, int(luks_parallel))

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

    def create_image_file(self, size_bytes: int) -> None:
        self.image_path.parent.mkdir(parents=True, exist_ok=True)
        allocation_timeout = max(self.filesystem_timeout_seconds, 900)
        try:
            self.run(
                "fallocate",
                "-l",
                str(size_bytes),
                str(self.image_path),
                timeout_seconds=allocation_timeout,
                reason="backend_error",
            )
            return
        except (self.storage_error, OSError):
            pass

        mb = 1024 * 1024
        whole_megabytes = size_bytes // mb
        remainder = size_bytes % mb
        try:
            self.run(
                "dd",
                "if=/dev/zero",
                f"of={self.image_path}",
                "bs=1M",
                f"count={whole_megabytes}",
                "conv=fsync",
                "status=none",
                timeout_seconds=allocation_timeout,
                reason="backend_error",
            )
            if remainder:
                self.run(
                    "dd",
                    "if=/dev/zero",
                    f"of={self.image_path}",
                    "bs=1",
                    f"count={remainder}",
                    f"seek={whole_megabytes * mb}",
                    "conv=notrunc",
                    "status=none",
                    timeout_seconds=allocation_timeout,
                    reason="backend_error",
                )
        except (self.storage_error, OSError) as exc:
            self.image_path.unlink(missing_ok=True)
            raise self.storage_error(f"failed to allocate vault image file: {exc}", reason="backend_error") from exc

        if not self.image_path.exists():
            raise self.storage_error("failed to create vault image file", reason="backend_error")

    def remove_image_file(self) -> None:
        self.image_path.unlink(missing_ok=True)

    def format_luks(self, passphrase: str) -> None:
        self.run(
            "cryptsetup",
            "luksFormat",
            "--type",
            "luks2",
            "--pbkdf",
            self.luks_pbkdf,
            "--iter-time",
            str(self.luks_iter_time_ms),
            "--pbkdf-memory",
            str(self.luks_memory_kib),
            "--pbkdf-parallel",
            str(self.luks_parallel),
            "--batch-mode",
            str(self.image_path),
            "-",
            input_text=passphrase,
            timeout_seconds=self.crypto_timeout_seconds,
            reason="backend_error",
        )

    def open_mapper(self, passphrase: str) -> None:
        self.run(
            "cryptsetup",
            "open",
            str(self.image_path),
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
            "NMOS_VAULT",
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
        image_created: bool,
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
                cleanup_errors.append(f"failed to unmount partially mounted vault: {exc}")

        if mapper_opened and self.mapper_path.exists():
            try:
                self.close_mapper()
            except (OSError, RuntimeError, ValueError) as exc:
                cleanup_errors.append(f"failed to close partially opened vault mapper: {exc}")

        if image_created and self.image_path.exists():
            try:
                self.remove_image_file()
            except OSError as exc:
                cleanup_errors.append(f"failed to remove partially created vault image: {exc}")
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
