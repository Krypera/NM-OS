#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
sys.path.insert(0, str(root / "apps" / "nmos_common"))
path = root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py"
spec = importlib.util.spec_from_file_location("nmos_storage", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeManager(module.PersistentStorageManager):
    def __init__(self):
        super().__init__()
        self._scenario = "ready"
        self.fail_create = False

    def locate_partition(self):
        if self._scenario == "existing":
            return "/dev/sdz3"
        return None

    def get_boot_disk_facts(self):
        if self._scenario == "unsupported":
            raise module.StorageError("boot medium is not a removable USB device", reason="unsupported_boot_device")
        if self._scenario == "read_only":
            return {"device": "/dev/sdz", "ro": "1"}
        return {"device": "/dev/sdz", "ro": "0"}

    def read_partition_table(self, disk: str):
        assert disk == "/dev/sdz"
        gib = 1024 * 1024 * 1024
        mib = 1024 * 1024
        if self._scenario == "unsupported_layout":
            raise module.StorageError("unsupported boot USB partition table label: bsd", reason="unsupported_layout")
        if self._scenario == "no_free_space":
            return {
                "device_size_bytes": 4 * gib,
                "sector_size": 512,
                "partitions": [{"number": 1, "start_bytes": 1 * mib, "size_bytes": (4 * gib) - (2 * mib)}],
            }
        return {
            "device_size_bytes": 8 * gib,
            "sector_size": 512,
            "partitions": [{"number": 1, "start_bytes": 1 * mib, "size_bytes": 2 * gib}],
        }

    def create_partition(self):
        if self.fail_create:
            raise module.StorageError("create failed", reason="backend_error")
        return {"path": "/dev/sdz2", "device": "/dev/sdz", "partition_number": 2}


with tempfile.TemporaryDirectory() as tmp:
    module.RUNTIME_DIR = Path(tmp)
    module.STATE_FILE = module.RUNTIME_DIR / "persistent-storage.json"
    module.MAPPER_PATH = Path(tmp) / "mapper"
    manager = FakeManager()

    manager._scenario = "unsupported"
    state = manager.get_state()
    assert state["boot_device_supported"] is False
    assert state["reason"] == "unsupported_boot_device"

    manager._scenario = "read_only"
    state = manager.get_state()
    assert state["boot_device_supported"] is True
    assert state["can_create"] is False
    assert state["reason"] == "read_only"

    manager._scenario = "existing"
    state = manager.get_state()
    assert state["created"] is True
    assert state["reason"] == "already_exists"

    manager._scenario = "no_free_space"
    state = manager.get_state()
    assert state["created"] is False
    assert state["can_create"] is False
    assert state["reason"] == "no_free_space"

    manager._scenario = "unsupported_layout"
    state = manager.get_state()
    assert state["created"] is False
    assert state["can_create"] is False
    assert state["reason"] == "unsupported_layout"

    manager._scenario = "ready"
    state = manager.get_state()
    assert state["created"] is False
    assert state["can_create"] is True
    assert state["reason"] == "ready"
    assert state["device"] == "/dev/sdz"

    manager.last_error = "temporary failure"
    state = manager.get_state()
    assert state["last_error"] == ""

    state = manager.get_state(include_cached_error=True)
    assert state["last_error"] == "temporary failure"

    manager.fail_create = True
    state = manager.create("secret")
    assert state["busy"] is False
    assert state["last_error"]
    manager.fail_create = False

    manager._scenario = "ready"
    state = manager.unlock("secret")
    assert state["busy"] is False
    assert state["last_error"]

    module.MAPPER_PATH.write_text("mapped", encoding="utf-8")
    mount_state = {"mounted": True}
    repair_commands: list[tuple[str, ...]] = []
    original_subprocess_run = module.subprocess.run
    original_run = manager.run
    original_get_state = manager.get_state

    def fake_subprocess_run(args, check=False, capture_output=False, text=False, **kwargs):
        if args[:2] == ["mountpoint", "-q"]:
            return SimpleNamespace(returncode=0 if mount_state["mounted"] else 1, stdout="", stderr="")
        if args and args[0] == "fsck.ext4" and "-n" in args:
            return SimpleNamespace(returncode=4, stdout="filesystem needs repair", stderr="")
        return original_subprocess_run(args, check=check, capture_output=capture_output, text=text, **kwargs)

    def fake_run(*args, input_text=None):
        del input_text
        repair_commands.append(tuple(args))
        if args[0] == "umount":
            mount_state["mounted"] = False
            return ""
        if args[0] == "mount":
            mount_state["mounted"] = True
            return ""
        if args[0] == "fsck.ext4":
            return ""
        return ""

    manager.get_state = lambda include_cached_error=False: {
        "busy": manager.busy,
        "last_error": manager.last_error if include_cached_error else "",
    }
    manager.run = fake_run
    module.subprocess.run = fake_subprocess_run
    try:
        state = manager.repair()
        assert state["busy"] is False
        assert [cmd[0] for cmd in repair_commands] == ["umount", "fsck.ext4", "mount"]
        assert mount_state["mounted"] is True

        module.MAPPER_PATH.unlink()
        repair_commands.clear()
        state = manager.repair()
        assert "must be unlocked" in state["last_error"]
        assert not any(cmd[0] == "fsck.ext4" for cmd in repair_commands)
    finally:
        manager.run = original_run
        manager.get_state = original_get_state
        module.subprocess.run = original_subprocess_run

print("Persistence state machine checks passed")
PY
