#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

network_bootstrap = load_module(
    "network_bootstrap",
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py",
)
tor_status = load_module(
    "tor_bootstrap_status",
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
)
storage = load_module(
    "nmos_storage",
    root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py",
)

sample = 'NOTICE BOOTSTRAP PROGRESS=67 TAG=conn_done SUMMARY="Connected to a relay"'
progress, summary = network_bootstrap.parse_bootstrap_status(sample)
assert progress == 67, progress
assert summary == "Connected to a relay", summary

progress2, summary2 = tor_status.parse_bootstrap_status(sample)
assert progress2 == 67, progress2
assert summary2 == "Connected to a relay", summary2

assert storage.boot_disk_is_supported("usb", False, False) is True
assert storage.boot_disk_is_supported(None, True, False) is True
assert storage.boot_disk_is_supported(None, False, True) is True
assert storage.boot_disk_is_supported("sata", False, False) is False
assert storage.partition_table_label_is_supported("gpt") is True
assert storage.partition_table_label_is_supported("dos") is True
assert storage.partition_table_label_is_supported("bsd") is False
assert hasattr(network_bootstrap, "remove_firewall_gate")

gib = 1024 * 1024 * 1024
mib = 1024 * 1024

single_partition_plan = storage.plan_trailing_partition(
    device_size_bytes=8 * gib,
    partitions=[
        {
            "number": 1,
            "start_bytes": 1 * mib,
            "size_bytes": 2 * gib,
        }
    ],
)
assert single_partition_plan["can_create"] is True
assert single_partition_plan["partition_number"] == 2
assert single_partition_plan["reason"] == "ready"

multi_partition_plan = storage.plan_trailing_partition(
    device_size_bytes=16 * gib,
    partitions=[
        {"number": 1, "start_bytes": 1 * mib, "size_bytes": 2 * gib},
        {"number": 2, "start_bytes": 3 * gib, "size_bytes": 4 * gib},
    ],
)
assert multi_partition_plan["can_create"] is True
assert multi_partition_plan["partition_number"] == 3
assert multi_partition_plan["free_bytes"] >= gib

full_disk_plan = storage.plan_trailing_partition(
    device_size_bytes=4 * gib,
    partitions=[
        {"number": 1, "start_bytes": 1 * mib, "size_bytes": (4 * gib) - (2 * mib)},
    ],
)
assert full_disk_plan["can_create"] is False
assert full_disk_plan["reason"] == "no_free_space"

print("runtime logic checks passed")
PY
