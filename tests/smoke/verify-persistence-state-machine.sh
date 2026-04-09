#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import tempfile
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
path = root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py"
spec = importlib.util.spec_from_file_location("nmos_storage", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeManager(module.PersistentStorageManager):
    def __init__(self):
        super().__init__()
        self._scenario = "ready"

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

print("Persistence state machine checks passed")
PY
