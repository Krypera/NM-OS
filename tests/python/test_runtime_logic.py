from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "nmos_common"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_greeter"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_persistent_storage"))

from nmos_common.system_settings import (
    DEFAULT_SYSTEM_SETTINGS,
    load_system_settings,
    normalize_system_settings,
    save_system_settings,
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_system_settings_round_trip(workspace_tmp_path: Path) -> None:
    persistent = workspace_tmp_path / "system-settings.json"
    runtime = workspace_tmp_path / "runtime-settings.json"

    saved = save_system_settings(
        {
            "locale": "es_ES.UTF-8",
            "keyboard": "tr",
            "network_policy": "direct",
            "allow_brave_browser": True,
        },
        persistent_path=persistent,
        runtime_path=runtime,
    )
    assert saved["network_policy"] == "direct"
    assert saved["allow_brave_browser"] is True

    loaded = load_system_settings(persistent_path=persistent, runtime_path=runtime)
    assert loaded["locale"] == "es_ES.UTF-8"
    assert loaded["keyboard"] == "tr"
    assert loaded["network_policy"] == "direct"
    assert loaded["allow_brave_browser"] is True

    assert normalize_system_settings({"network_policy": "invalid"})["network_policy"] == "tor"
    assert load_system_settings(
        persistent_path=workspace_tmp_path / "missing.json",
        runtime_path=workspace_tmp_path / "also-missing.json",
    ) == DEFAULT_SYSTEM_SETTINGS


def test_tor_status_respects_settings(repo_root: Path, workspace_tmp_path: Path) -> None:
    tor_status = load_module(
        "tor_bootstrap_status",
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
    )
    tor_status.READY_FILE = workspace_tmp_path / "network-ready"
    tor_status.STATUS_FILE = workspace_tmp_path / "network-status.json"
    tor_status.load_system_settings = lambda: {"network_policy": "offline"}
    disabled_state = tor_status.read_status()
    assert disabled_state["phase"] == "disabled"

    tor_status.load_system_settings = lambda: {"network_policy": "direct"}
    direct_state = tor_status.read_status()
    assert direct_state["phase"] == "open"
    assert direct_state["ready"] is True

    tor_status.load_system_settings = lambda: {"network_policy": "tor"}
    tor_status.READY_FILE.write_text("ready\n", encoding="utf-8")
    ready_state = tor_status.read_status()
    assert ready_state["ready"] is True
    assert ready_state["summary"] == "Tor is ready"


def test_runtime_state_and_overlay_bootstrap_use_hardened_writes(repo_root: Path) -> None:
    runtime_state_source = (repo_root / "apps" / "nmos_common" / "nmos_common" / "runtime_state.py").read_text(
        encoding="utf-8"
    )
    settings_bootstrap_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "settings_bootstrap.py"
    ).read_text(encoding="utf-8")
    network_bootstrap_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py"
    ).read_text(encoding="utf-8")

    assert "O_NOFOLLOW" in runtime_state_source
    assert "mkstemp" in runtime_state_source
    assert "os.fsync" in runtime_state_source
    assert "os.replace" in runtime_state_source
    assert "write_runtime_json" in settings_bootstrap_source
    assert "load_system_settings" in settings_bootstrap_source
    assert "write_runtime_json" in network_bootstrap_source
    assert "write_runtime_text" in network_bootstrap_source


def test_greeter_layout_is_setup_only(repo_root: Path) -> None:
    main_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "main.py").read_text(encoding="utf-8")
    ui_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "ui_composition.py").read_text(
        encoding="utf-8"
    )

    assert "save_system_settings" in main_source
    assert "GDM" not in main_source
    assert "network_policy_combo" in ui_source
    assert "allow_brave_browser" in ui_source
    assert not (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "gdmclient.py").exists()
    assert not (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "gdm_handoff.py").exists()


def test_vault_storage_is_file_based(repo_root: Path, workspace_tmp_path: Path) -> None:
    storage = load_module(
        "nmos_storage",
        repo_root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py",
    )
    storage.RUNTIME_DIR = workspace_tmp_path / "run"
    storage.STATE_FILE = storage.RUNTIME_DIR / "persistent-storage.json"
    storage.STORAGE_ROOT = workspace_tmp_path / "var" / "lib" / "nmos" / "storage"
    storage.VAULT_IMAGE_PATH = storage.STORAGE_ROOT / "vault.img"
    storage.MOUNT_POINT = storage.STORAGE_ROOT / "mnt"
    storage.MAPPER_PATH = workspace_tmp_path / "mapper"

    manager = storage.PersistentStorageManager()
    state = manager.get_state()
    assert state["path"].endswith("vault.img")
    assert state["reason"] in {"ready", "no_space"}

    storage.VAULT_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    storage.VAULT_IMAGE_PATH.write_bytes(b"")
    state = manager.get_state()
    assert state["created"] is True
    assert state["reason"] == "already_exists"

    source = (repo_root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py").read_text(
        encoding="utf-8"
    )
    assert "/run/live/medium" not in source
    assert "/live/persistence" not in source


def test_brave_visibility_and_runtime_share_settings_helper(repo_root: Path) -> None:
    desktop_mode_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "desktop_mode.py"
    ).read_text(encoding="utf-8")
    brave_policy_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "brave_policy.py"
    ).read_text(encoding="utf-8")

    assert "load_system_settings" in desktop_mode_source
    assert "load_system_settings" in brave_policy_source
    assert 'allow_brave_browser' in desktop_mode_source
    assert 'allow_brave_browser' in brave_policy_source


def test_overlay_build_uses_installed_python_packages(repo_root: Path) -> None:
    common_source = (repo_root / "build" / "lib" / "common.sh").read_text(encoding="utf-8")
    greeter_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-greeter"
    ).read_text(encoding="utf-8")
    persistence_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-persistent-storage"
    ).read_text(encoding="utf-8")

    assert "install_python_package_dir" in common_source
    assert "/usr/lib/python3/dist-packages" in common_source
    assert "PYTHONPATH" not in greeter_launcher_source
    assert "PYTHONPATH" not in persistence_launcher_source


def test_service_units_include_requested_hardening(repo_root: Path) -> None:
    persistent_service = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-persistent-storage.service"
    ).read_text(encoding="utf-8")
    network_service = (
        repo_root
        / "config"
        / "system-overlay"
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
    assert "ReadWritePaths=/run/nmos /var/lib/nmos" in persistent_service
    assert "ReadWritePaths=/run/nmos" in network_service
    assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK" in network_service


def test_workflow_includes_overlay_and_windows_validation(repo_root: Path) -> None:
    workflow_source = (repo_root / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "build-smoke:" in workflow_source
    assert "smoke-overlay.sh" in workflow_source
    assert "windows-smoke:" in workflow_source
    assert "verify-windows-wsl-bridge.ps1" in workflow_source


def test_i18n_supports_spanish_without_extra_locales(repo_root: Path) -> None:
    i18n_source = (repo_root / "apps" / "nmos_common" / "nmos_common" / "i18n.py").read_text(encoding="utf-8")
    assert "es_ES.UTF-8" in i18n_source
    for unsupported_locale in ("tr_TR.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"):
        assert unsupported_locale not in i18n_source
