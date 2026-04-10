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


def test_brave_visibility_and_runtime_share_feature_flag_helper(repo_root: Path) -> None:
    desktop_mode_source = (
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "desktop_mode.py"
    ).read_text(encoding="utf-8")
    brave_policy_source = (
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "brave_policy.py"
    ).read_text(encoding="utf-8")

    assert "load_feature_flag" in desktop_mode_source
    assert "load_feature_flag" in brave_policy_source
    assert 'if brave_enabled and mode == "flexible":' in desktop_mode_source
    assert "return load_feature_flag(BRAVE_FEATURE_FILE)" in brave_policy_source


def test_optional_brave_hook_verifies_pinned_key_fingerprints(repo_root: Path) -> None:
    brave_hook_source = (
        repo_root / "hooks" / "optional" / "050-install-brave-browser.hook.chroot"
    ).read_text(encoding="utf-8")

    assert "ALLOWED_BRAVE_FINGERPRINTS" in brave_hook_source
    assert "verify_brave_keyring_fingerprint" in brave_hook_source
    assert "gpg --show-keys --with-colons" in brave_hook_source


def test_runtime_launchers_use_installed_python_packages(repo_root: Path) -> None:
    install_hook_source = (repo_root / "hooks" / "live" / "010-install-nmos-apps.hook.chroot").read_text(
        encoding="utf-8"
    )
    greeter_launcher_source = (
        repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "bin" / "nmos-greeter"
    ).read_text(encoding="utf-8")
    persistence_launcher_source = (
        repo_root
        / "config"
        / "live-build"
        / "includes.chroot"
        / "usr"
        / "local"
        / "bin"
        / "nmos-persistent-storage"
    ).read_text(encoding="utf-8")

    assert "install_python_package_dir /opt/nmos/apps/nmos_common/nmos_common" in install_hook_source
    assert "install_python_package_dir /opt/nmos/apps/nmos_greeter/nmos_greeter" in install_hook_source
    assert "install_python_package_dir /opt/nmos/apps/nmos_persistent_storage/nmos_persistent_storage" in install_hook_source
    assert "PYTHONPATH" not in greeter_launcher_source
    assert "PYTHONPATH" not in persistence_launcher_source


def test_service_units_include_requested_hardening(repo_root: Path) -> None:
    persistent_service = (
        repo_root
        / "config"
        / "live-build"
        / "includes.chroot"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-persistent-storage.service"
    ).read_text(encoding="utf-8")
    network_service = (
        repo_root
        / "config"
        / "live-build"
        / "includes.chroot"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-network-bootstrap.service"
    ).read_text(encoding="utf-8")

    for value in ("NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=yes", "PrivateTmp=yes"):
        assert value in persistent_service
        assert value in network_service

    assert "CapabilityBoundingSet=" in persistent_service
    assert "CapabilityBoundingSet=" in network_service
    assert "ReadWritePaths=/run/nmos /live/persistence" in persistent_service
    assert "ReadWritePaths=/run/nmos" in network_service
    assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK" in network_service


def test_workflow_includes_windows_bridge_validation(repo_root: Path) -> None:
    workflow_source = (repo_root / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "windows-smoke:" in workflow_source
    assert "verify-windows-wsl-bridge.ps1" in workflow_source
