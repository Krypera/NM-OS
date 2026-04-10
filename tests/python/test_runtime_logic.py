from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "nmos_common"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_greeter"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_persistent_storage"))

from nmos_common.boot_mode import boot_mode_profile, parse_mode_from_cmdline
from nmos_common.config_helpers import load_mode, read_assignment_file
from nmos_persistent_storage.partition_planning import (
    boot_disk_is_supported,
    partition_table_label_is_supported,
    plan_trailing_partition,
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bootstrap_parser_consistency(repo_root: Path) -> None:
    network_bootstrap = load_module(
        "network_bootstrap",
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py",
    )
    tor_status = load_module(
        "tor_bootstrap_status",
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
    )
    sample = 'NOTICE BOOTSTRAP PROGRESS=67 TAG=conn_done SUMMARY="Connected to a relay"'
    progress, summary = network_bootstrap.parse_bootstrap_status(sample)
    assert progress == 67
    assert summary == "Connected to a relay"

    progress2, summary2 = tor_status.parse_bootstrap_status(sample)
    assert progress2 == 67
    assert summary2 == "Connected to a relay"


def test_tor_status_prefers_runtime_files(repo_root: Path, workspace_tmp_path: Path) -> None:
    tor_status = load_module(
        "tor_bootstrap_status",
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
    )
    tor_status.READY_FILE = workspace_tmp_path / "network-ready"
    tor_status.STATUS_FILE = workspace_tmp_path / "network-status.json"

    tor_status.READY_FILE.write_text("ready\n", encoding="utf-8")
    ready_state = tor_status.read_status()
    assert ready_state["ready"] is True
    assert ready_state["last_error"] == ""

    tor_status.READY_FILE.unlink()
    tor_status.STATUS_FILE.write_text('{"ready": false, "progress": 13, "summary": "Testing"}', encoding="utf-8")
    file_state = tor_status.read_status()
    assert file_state["ready"] is False
    assert file_state["progress"] == 13
    assert file_state["summary"] == "Testing"
    assert file_state["last_error"] == ""


def test_partition_planning_helpers() -> None:
    assert boot_disk_is_supported("usb", False, False) is True
    assert boot_disk_is_supported(None, True, False) is True
    assert boot_disk_is_supported(None, False, True) is False
    assert boot_disk_is_supported("sata", False, False) is False
    assert partition_table_label_is_supported("gpt") is True
    assert partition_table_label_is_supported("dos") is False

    gib = 1024 * 1024 * 1024
    mib = 1024 * 1024
    plan = plan_trailing_partition(
        device_size_bytes=8 * gib,
        partitions=[{"number": 1, "start_bytes": 1 * mib, "size_bytes": 2 * gib}],
    )
    assert plan["can_create"] is True
    assert plan["partition_number"] == 2
    assert plan["reason"] == "ready"


def test_boot_mode_profile_behavior() -> None:
    assert parse_mode_from_cmdline("quiet splash nmos.mode=recovery") == "recovery"
    assert parse_mode_from_cmdline("quiet splash nmos.mode=invalid") == "strict"
    assert boot_mode_profile("offline")["network_policy"] == "disabled"
    assert boot_mode_profile("compat")["compat_enabled"] is True


def test_runtime_state_and_bootstrap_use_hardened_writes(repo_root: Path) -> None:
    runtime_state_source = (repo_root / "apps" / "nmos_common" / "nmos_common" / "runtime_state.py").read_text(
        encoding="utf-8"
    )
    network_bootstrap_source = (
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py"
    ).read_text(encoding="utf-8")

    assert "O_NOFOLLOW" in runtime_state_source
    assert "mkstemp" in runtime_state_source
    assert "os.fsync" in runtime_state_source
    assert "os.replace" in runtime_state_source
    assert "write_runtime_json" in network_bootstrap_source
    assert "write_runtime_text" in network_bootstrap_source
    assert "STATUS_FILE.write_text" not in network_bootstrap_source
    assert "READY_FILE.write_text" not in network_bootstrap_source


def test_greeter_modular_layout_and_handoff(repo_root: Path) -> None:
    main_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "main.py").read_text(encoding="utf-8")
    gdm_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "gdmclient.py").read_text(encoding="utf-8")
    assert "from nmos_greeter import gdm_handoff, network_model, persistence_actions, ui_composition" in main_source
    assert "def cancel_pending_login" in gdm_source


def test_persistent_storage_manager_uses_layered_modules(repo_root: Path) -> None:
    storage_source = (
        repo_root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py"
    ).read_text(encoding="utf-8")
    assert "DiskDiscovery" in storage_source
    assert "CryptoMountOps" in storage_source
    assert "build_state_payload" in storage_source
    assert 'REASON_TIMEOUT = "command_timeout"' in storage_source


def test_common_helper_read_assignment_and_load_mode(workspace_tmp_path: Path) -> None:
    env_file = workspace_tmp_path / "env.conf"
    env_file.write_text(
        "# demo\nLIVE_USERNAME='nmos'\nLIVE_PASSWORD=test123\nINVALID_LINE\n",
        encoding="utf-8",
    )
    parsed = read_assignment_file(env_file)
    assert parsed["LIVE_USERNAME"] == "nmos"
    assert parsed["LIVE_PASSWORD"] == "test123"

    mode_file = workspace_tmp_path / "boot-mode.json"
    mode_file.write_text(json.dumps({"mode": "flexible"}), encoding="utf-8")
    assert load_mode(mode_file) == "flexible"
