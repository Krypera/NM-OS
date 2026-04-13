from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "nmos_common"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_greeter"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_persistent_storage"))
sys.path.insert(0, str(ROOT / "apps" / "nmos_settings"))

from nmos_common.i18n import (
    TRANSLATIONS,
    display_language_name,
    display_setting_value,
    explain_brave_visibility,
    explain_device_policy,
    explain_logging_policy,
    explain_network_policy,
    explain_sandbox_default,
    explain_vault_behavior,
    format_change_detail,
    format_posture_shift,
    posture_explanation_lines,
    posture_meter_lines,
    translate,
)
from nmos_common.platform_adapter import load_platform_adapter
from nmos_common.settings_client import SettingsClient, SettingsClientError
from nmos_common.system_settings import (
    DEFAULT_SYSTEM_SETTINGS,
    apply_system_profile,
    classify_effective_changes,
    compute_posture_score_shift,
    compute_posture_scores,
    derive_overrides_for_profile,
    describe_effective_change_details,
    describe_posture_preview,
    extract_effective_settings,
    load_effective_system_settings,
    load_system_settings,
    normalize_system_settings,
    save_system_settings,
    setting_display_name,
    update_system_overrides,
)
from nmos_settings.authorization import build_write_uid_allowlist, is_write_authorized


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
    applied = workspace_tmp_path / "applied-settings.json"

    saved = save_system_settings(
        {
            "active_profile": "hardened",
            "overrides": {
                "locale": "es_ES.UTF-8",
                "keyboard": "tr",
                "network_policy": "direct",
                "allow_brave_browser": True,
                "ui_theme_profile": "nmos-light",
                "default_browser": "chromium",
            },
        },
        persistent_path=persistent,
        runtime_path=runtime,
        applied_path=applied,
    )
    assert saved["schema_version"] == 1
    assert saved["active_profile"] == "hardened"
    assert saved["network_policy"] == "direct"
    assert saved["allow_brave_browser"] is True
    assert saved["sandbox_default"] == "strict"
    assert "network_policy" in saved["pending_reboot"]
    assert "sandbox_default" in saved["pending_reboot"]

    loaded = load_system_settings(persistent_path=persistent, runtime_path=runtime, applied_path=applied)
    assert loaded["locale"] == "es_ES.UTF-8"
    assert loaded["keyboard"] == "tr"
    assert loaded["network_policy"] == "direct"
    assert loaded["allow_brave_browser"] is True
    assert loaded["ui_theme_profile"] == "nmos-light"
    assert loaded["default_browser"] == "chromium"
    assert extract_effective_settings(loaded)["active_profile"] == "hardened"
    assert load_effective_system_settings(persistent_path=persistent, runtime_path=runtime, applied_path=applied)[
        "sandbox_default"
    ] == "strict"

    assert normalize_system_settings({"network_policy": "invalid"})["network_policy"] == "tor"
    assert load_system_settings(
        persistent_path=workspace_tmp_path / "missing.json",
        runtime_path=workspace_tmp_path / "also-missing.json",
    ) == DEFAULT_SYSTEM_SETTINGS

    saved = apply_system_profile(
        "relaxed",
        persistent_path=persistent,
        runtime_path=runtime,
        applied_path=applied,
    )
    assert saved["active_profile"] == "relaxed"
    assert saved["network_policy"] == "direct"

    updated = update_system_overrides(
        derive_overrides_for_profile(
            "relaxed",
            {"network_policy": "offline", "logging_policy": "sealed", "default_browser": "chromium"},
        ),
        persistent_path=persistent,
        runtime_path=runtime,
        applied_path=applied,
    )
    assert updated["network_policy"] == "offline"
    assert updated["default_browser"] == "chromium"
    assert "network_policy" in updated["pending_reboot"]


def test_platform_adapter_override_loading(workspace_tmp_path: Path) -> None:
    adapter_file = workspace_tmp_path / "platform-adapter.env"
    adapter_file.write_text(
        "\n".join(
            [
                "NMOS_TOR_USER=test-tor",
                "NMOS_GDM_USER=test-gdm",
                "NMOS_SETTINGS_ADMIN_GROUP=wheel",
                "NMOS_RUNTIME_DIR=/tmp/nmos-run",
                "NMOS_STATE_DIR=/tmp/nmos-state",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    loaded = load_platform_adapter(adapter_file)
    assert loaded["tor_user"] == "test-tor"
    assert loaded["gdm_user"] == "test-gdm"
    assert loaded["settings_admin_group"] == "wheel"
    assert loaded["runtime_dir"] == "/tmp/nmos-run"
    assert loaded["state_dir"] == "/tmp/nmos-state"

    original_runtime = os.environ.get("NMOS_RUNTIME_DIR")
    os.environ["NMOS_RUNTIME_DIR"] = "/tmp/env-run"
    try:
        env_loaded = load_platform_adapter(adapter_file)
    finally:
        if original_runtime is None:
            os.environ.pop("NMOS_RUNTIME_DIR", None)
        else:
            os.environ["NMOS_RUNTIME_DIR"] = original_runtime
    assert env_loaded["runtime_dir"] == "/tmp/env-run"


class _MockBackendUnavailableDBusError(Exception):
    def get_dbus_name(self) -> str:
        return "org.freedesktop.DBus.Error.ServiceUnknown"


class _MockDeniedDBusError(Exception):
    def get_dbus_name(self) -> str:
        return "org.freedesktop.DBus.Error.AccessDenied"


class _MockRetriableDBusError(Exception):
    def get_dbus_name(self) -> str:
        return "org.freedesktop.DBus.Error.TimedOut"


def test_settings_client_does_not_fallback_by_default() -> None:
    client = SettingsClient(allow_local_fallback=False)
    client._interface = lambda _interface: (_ for _ in ()).throw(_MockRetriableDBusError())  # type: ignore[method-assign]
    try:
        client.get_settings()
        assert False, "Expected SettingsClientError when fallback is disabled"
    except SettingsClientError as error:
        assert error.reason == "transport_error"
        assert "connection failed" in error.user_message().lower()


def test_settings_client_backend_unavailable_reason_is_explicit() -> None:
    client = SettingsClient(allow_local_fallback=False)
    client._interface = lambda _interface: (_ for _ in ()).throw(_MockBackendUnavailableDBusError())  # type: ignore[method-assign]
    try:
        client.get_settings()
        assert False, "Expected SettingsClientError when backend is unavailable"
    except SettingsClientError as error:
        assert error.reason == "backend_unavailable"
        assert "unavailable" in error.user_message().lower()


def test_settings_client_retriable_fallback_is_opt_in() -> None:
    client = SettingsClient(allow_local_fallback=True)
    client._interface = lambda _interface: (_ for _ in ()).throw(_MockRetriableDBusError())  # type: ignore[method-assign]
    client.local.get_settings = lambda: {"source": "local"}  # type: ignore[method-assign]
    assert client.get_settings() == {"source": "local"}


def test_settings_client_access_denied_never_falls_back() -> None:
    client = SettingsClient(allow_local_fallback=True)
    client._interface = lambda _interface: (_ for _ in ()).throw(_MockDeniedDBusError())  # type: ignore[method-assign]
    try:
        client.get_settings()
        assert False, "Expected SettingsClientError for access denied"
    except SettingsClientError as error:
        assert error.reason == "access_denied"
        assert "denied access" in error.user_message().lower()


def test_settings_client_uses_read_write_interfaces() -> None:
    client = SettingsClient(allow_local_fallback=False)
    called_interfaces: list[str] = []

    class _FakeInterface:
        def __init__(self, interface_name: str) -> None:
            self.interface_name = interface_name

        def GetSettings(self):
            called_interfaces.append(self.interface_name)
            return {"active_profile": "balanced"}

        def GetPendingRebootChanges(self):
            called_interfaces.append(self.interface_name)
            return ["network_policy"]

        def Commit(self):
            called_interfaces.append(self.interface_name)
            return {"active_profile": "balanced"}

    client._interface = lambda interface_name: _FakeInterface(interface_name)  # type: ignore[method-assign]
    client.get_settings()
    client.get_pending_reboot_changes()
    client.commit()

    assert called_interfaces[0] == "org.nmos.Settings1.Read"
    assert called_interfaces[1] == "org.nmos.Settings1.Read"
    assert called_interfaces[2] == "org.nmos.Settings1.Write"


def test_settings_write_allowlist_always_includes_root(monkeypatch) -> None:
    monkeypatch.setattr("nmos_settings.authorization.resolve_unix_uid", lambda _name: None)
    monkeypatch.setattr("nmos_settings.authorization.resolve_group_member_uids", lambda _group: set())
    allowlist = build_write_uid_allowlist("Debian-gdm", "sudo")
    assert allowlist == {0}


def test_settings_write_allowlist_includes_gdm_uid_when_resolved(monkeypatch) -> None:
    monkeypatch.setattr("nmos_settings.authorization.resolve_unix_uid", lambda _name: 120)
    monkeypatch.setattr("nmos_settings.authorization.resolve_group_member_uids", lambda _group: {1000, 1001})
    allowlist = build_write_uid_allowlist("Debian-gdm", "sudo")
    assert allowlist == {0, 120, 1000, 1001}


def test_settings_write_authorization_requires_uid_match() -> None:
    allowlist = {0, 120}
    assert is_write_authorized(0, allowlist) is True
    assert is_write_authorized(120, allowlist) is True
    assert is_write_authorized(1000, allowlist) is False


def test_posture_preview_is_explainable() -> None:
    posture = describe_posture_preview(
        "balanced",
        {
            "network_policy": "direct",
            "allow_brave_browser": True,
            "vault": {
                "enabled": True,
                "auto_lock_minutes": 5,
                "unlock_on_login": True,
            },
        },
    )

    assert posture["profile"] == "balanced"
    assert posture["ideal_for"] == "Best for most people who want a clear privacy baseline without a harsh learning curve."
    assert posture["effective"]["network_policy"] == "direct"
    assert posture["effective"]["vault"]["auto_lock_minutes"] == 5
    assert posture["effective"]["allow_brave_browser"] is True
    assert posture["scores"]["protection"] <= posture["scores"]["convenience"]
    assert 0 <= posture["scores"]["protection"] <= 10
    assert 0 <= posture["scores"]["convenience"] <= 10

    english_lines = posture_explanation_lines("en_US.UTF-8", posture)
    assert any("Direct networking keeps the desktop familiar and compatible" in line for line in english_lines)
    assert any("Vault auto-locks after 5 minutes" in line for line in english_lines)
    assert any("Brave can appear when it is installed" in line for line in english_lines)

    spanish_lines = posture_explanation_lines("es_ES.UTF-8", posture)
    assert any("red directa" in line.lower() for line in spanish_lines)
    assert any("5 minutos" in line for line in spanish_lines)
    meter_lines = posture_meter_lines("es_ES.UTF-8", posture)
    assert any("Nivel de protección" in line for line in meter_lines)


def test_posture_scores_reflect_stricter_defaults() -> None:
    relaxed = compute_posture_scores(
        {
            "network_policy": "direct",
            "sandbox_default": "standard",
            "device_policy": "shared",
            "logging_policy": "balanced",
            "allow_brave_browser": True,
            "vault": {"auto_lock_minutes": 0, "unlock_on_login": True},
        }
    )
    maximum = compute_posture_scores(
        {
            "network_policy": "offline",
            "sandbox_default": "strict",
            "device_policy": "locked",
            "logging_policy": "sealed",
            "allow_brave_browser": False,
            "vault": {"auto_lock_minutes": 1, "unlock_on_login": False},
        }
    )
    assert maximum["protection"] > relaxed["protection"]
    assert maximum["convenience"] < relaxed["convenience"]
    shift = compute_posture_score_shift(relaxed, maximum)
    assert shift["protection_delta"] > 0
    assert shift["convenience_delta"] < 0
    shift_text = format_posture_shift("en_US.UTF-8", shift)
    assert "protection +" in shift_text
    assert "convenience -" in shift_text


def test_setting_specific_explanations_are_stable() -> None:
    assert "privacy-first default" in explain_network_policy("en_US.UTF-8", "tor")
    assert "Red directa" not in explain_network_policy("en_US.UTF-8", "direct")
    assert "red directa" in explain_network_policy("es_ES.UTF-8", "direct").lower()

    assert "containment boundaries" in explain_sandbox_default("en_US.UTF-8", "focused")
    assert "dispositivos externos" in explain_device_policy("es_ES.UTF-8", "prompt")
    assert "diagnostics" in explain_logging_policy("en_US.UTF-8", "balanced")

    vault_lines = explain_vault_behavior(
        "en_US.UTF-8",
        {"auto_lock_minutes": 0, "unlock_on_login": False},
    )
    assert any("manual" in line for line in vault_lines)
    assert any("explicitly unlock" in line for line in vault_lines)

    assert "Brave can appear" in explain_brave_visibility("en_US.UTF-8", True, "direct")
    assert "Brave stays hidden" in explain_brave_visibility("en_US.UTF-8", True, "offline")


def test_change_classification_groups_now_and_reboot() -> None:
    draft = {
        "active_profile": "balanced",
        "overrides": {
            "network_policy": "direct",
            "ui_accent": "mint",
            "allow_brave_browser": True,
            "default_browser": "chromium",
        },
    }
    applied = {
        "active_profile": "balanced",
        "locale": "en_US.UTF-8",
        "keyboard": "us",
        "network_policy": "tor",
        "allow_brave_browser": False,
        "sandbox_default": "focused",
        "vault": {"enabled": True, "auto_lock_minutes": 15, "unlock_on_login": False},
        "device_policy": "prompt",
        "logging_policy": "minimal",
        "ui_theme_profile": "nmos-classic",
        "ui_accent": "amber",
        "ui_density": "comfortable",
        "ui_motion": "full",
        "default_browser": "firefox-esr",
    }
    grouped = classify_effective_changes(draft, applied_settings=applied)
    detailed = describe_effective_change_details(draft, applied_settings=applied)
    assert "network_policy" in grouped["reboot"]
    assert "allow_brave_browser" in grouped["immediate"]
    assert "ui_accent" in grouped["immediate"]
    assert "default_browser" in grouped["immediate"]
    assert any(item["key"] == "network_policy" and item["from"] == "tor" and item["to"] == "direct" for item in detailed["reboot"])
    assert any(item["key"] == "ui_accent" and item["from"] == "amber" and item["to"] == "mint" for item in detailed["immediate"])
    assert setting_display_name("network_policy") == "Network policy"
    assert setting_display_name("unknown_field") == "Unknown Field"


def test_change_detail_formatting_is_human_readable() -> None:
    assert display_setting_value("en_US.UTF-8", "network_policy", "tor") == "Tor-first"
    assert "Activado" == display_setting_value("es_ES.UTF-8", "allow_brave_browser", True)
    assert "manual" in display_setting_value("en_US.UTF-8", "vault", {"auto_lock_minutes": 0, "unlock_on_login": False}).lower()
    detail = format_change_detail("en_US.UTF-8", "Network policy", "network_policy", "tor", "offline")
    assert "Network policy: Tor-first -> Offline" == detail


def test_tor_status_respects_settings(repo_root: Path, workspace_tmp_path: Path) -> None:
    tor_status = load_module(
        "tor_bootstrap_status",
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
    )
    tor_status.READY_FILE = workspace_tmp_path / "network-ready"
    tor_status.STATUS_FILE = workspace_tmp_path / "network-status.json"
    tor_status.load_effective_system_settings = lambda: {"network_policy": "offline"}
    disabled_state = tor_status.read_status()
    assert disabled_state["phase"] == "disabled"

    tor_status.load_effective_system_settings = lambda: {"network_policy": "direct"}
    direct_state = tor_status.read_status()
    assert direct_state["phase"] == "open"
    assert direct_state["ready"] is True

    tor_status.load_effective_system_settings = lambda: {"network_policy": "tor"}
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
    assert "save_system_settings" in settings_bootstrap_source
    assert "APPLIED_SETTINGS_FILE" in settings_bootstrap_source
    assert "load_system_settings" in settings_bootstrap_source
    system_settings_source = (
        repo_root / "apps" / "nmos_common" / "nmos_common" / "system_settings.py"
    ).read_text(encoding="utf-8")
    assert "get_runtime_dir" in system_settings_source
    assert "get_state_dir" in system_settings_source
    assert "write_runtime_json" in network_bootstrap_source
    assert "write_runtime_text" in network_bootstrap_source
    assert "get_tor_user" in network_bootstrap_source
    assert '"debian-tor"' not in network_bootstrap_source


def test_greeter_layout_is_setup_only(repo_root: Path) -> None:
    main_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "main.py").read_text(encoding="utf-8")
    ui_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "ui_composition.py").read_text(
        encoding="utf-8"
    )

    assert "SettingsClient" in main_source
    assert "allow_local_fallback=False" in main_source
    assert "describe_backend_issue" in main_source
    assert "backend_recovery_hint" in main_source
    assert "authorized session" in main_source
    assert "service health" in main_source
    assert "Action: sign in with an admin-authorized session and retry." in main_source
    assert "Review mode only until service is reachable." in main_source
    assert "GDM" not in main_source
    assert "profile_combo" in ui_source
    assert "network_policy_combo" in ui_source
    assert "theme_profile_combo" in ui_source
    assert "allow_brave_browser" in ui_source
    assert "default_browser" in ui_source
    state_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "state.py").read_text(encoding="utf-8")
    client_source = (repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "client.py").read_text(encoding="utf-8")
    network_model_source = (
        repo_root / "apps" / "nmos_greeter" / "nmos_greeter" / "network_model.py"
    ).read_text(encoding="utf-8")
    assert "get_runtime_dir" in state_source
    assert "get_runtime_dir" in client_source
    assert "get_runtime_dir" in network_model_source
    assert 'Path("/run/nmos' not in state_source
    assert 'Path("/run/nmos' not in client_source
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

    assert "load_effective_system_settings" in desktop_mode_source
    assert "load_effective_system_settings" in brave_policy_source
    assert 'allow_brave_browser' in desktop_mode_source
    assert 'allow_brave_browser' in brave_policy_source
    assert 'default_browser' in desktop_mode_source
    assert "default-web-browser" in desktop_mode_source
    assert "x-scheme-handler/http" in desktop_mode_source
    assert "x-scheme-handler/https" in desktop_mode_source
    assert "session-appearance.json" in desktop_mode_source
    assert "gsettings" in desktop_mode_source
    assert "picture-uri" in desktop_mode_source
    assert "enable-animations" in desktop_mode_source
    assert "text-scaling-factor" in desktop_mode_source
    assert "wallpaper-night.svg" in desktop_mode_source
    assert "wallpaper-light.svg" in desktop_mode_source


def test_default_browser_enforcement_composes_expected_commands(repo_root: Path) -> None:
    desktop_mode = load_module(
        "desktop_mode",
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "desktop_mode.py",
    )
    commands: list[list[str]] = []

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(command, **_kwargs):
        commands.append(list(command))
        return _Completed()

    desktop_mode.subprocess.run = _fake_run
    desktop_mode.apply_default_browser({"default_browser": "chromium"})

    assert commands[0] == ["xdg-settings", "set", "default-web-browser", "chromium.desktop"]
    assert commands[1] == ["gio", "mime", "x-scheme-handler/http", "chromium.desktop"]
    assert commands[2] == ["gio", "mime", "x-scheme-handler/https", "chromium.desktop"]

    commands.clear()
    desktop_mode.apply_default_browser({"default_browser": "none"})
    assert commands == []


def test_logging_policy_enforcement_assets_exist(repo_root: Path) -> None:
    logging_policy_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "logging_policy.py"
    ).read_text(encoding="utf-8")
    logging_service_source = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-logging-policy.service"
    ).read_text(encoding="utf-8")
    assert "load_effective_system_settings" in logging_policy_source
    assert "journald.conf.d" in logging_policy_source
    assert "journalctl" in logging_policy_source
    assert "systemd-journald.service" in logging_policy_source
    assert "NMOS_LOGGING_POLICY" in logging_policy_source
    assert "ExecStart=/usr/local/lib/nmos/logging_policy.py" in logging_service_source


def test_app_isolation_enforcement_assets_exist(repo_root: Path) -> None:
    app_isolation_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "app_isolation_policy.py"
    ).read_text(encoding="utf-8")
    app_isolation_service_source = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-app-isolation-policy.service"
    ).read_text(encoding="utf-8")
    assert "load_effective_system_settings" in app_isolation_source
    assert "flatpak" in app_isolation_source
    assert "policy_commands" in app_isolation_source
    assert "app-isolation-status.json" in app_isolation_source
    assert "ExecStart=/usr/local/lib/nmos/app_isolation_policy.py" in app_isolation_service_source


def test_app_isolation_policy_composes_expected_flatpak_commands(repo_root: Path) -> None:
    app_isolation = load_module(
        "app_isolation_policy",
        repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos" / "app_isolation_policy.py",
    )
    assert app_isolation.policy_commands("standard") == [
        ["flatpak", "override", "--system", "--reset"],
        ["flatpak", "override", "--system", "--filesystem=home"],
    ]
    assert app_isolation.policy_commands("focused") == [
        ["flatpak", "override", "--system", "--reset"],
        ["flatpak", "override", "--system", "--nofilesystem=host"],
    ]
    assert app_isolation.policy_commands("strict") == [
        ["flatpak", "override", "--system", "--reset"],
        ["flatpak", "override", "--system", "--nofilesystem=home", "--nofilesystem=host"],
    ]


def test_overlay_build_uses_installed_python_packages(repo_root: Path) -> None:
    common_source = (repo_root / "build" / "lib" / "common.sh").read_text(encoding="utf-8")
    greeter_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-greeter"
    ).read_text(encoding="utf-8")
    settings_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-settings-service"
    ).read_text(encoding="utf-8")
    control_center_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-control-center"
    ).read_text(encoding="utf-8")
    persistence_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-persistent-storage"
    ).read_text(encoding="utf-8")

    assert "install_python_package_dir" in common_source
    assert "/usr/lib/python3/dist-packages" in common_source
    assert "nmos_settings/nmos_settings" in common_source
    assert "nmos_control_center/nmos_control_center" in common_source
    assert "nmos_help/nmos_help" in common_source
    assert "docs/user-guides" in common_source
    assert "/usr/share/doc/nmos/user-guides/" in common_source
    platform_adapter_source = (repo_root / "apps" / "nmos_common" / "nmos_common" / "platform_adapter.py").read_text(
        encoding="utf-8"
    )
    assert "NMOS_TOR_USER" in platform_adapter_source
    assert "NMOS_GDM_USER" in platform_adapter_source
    assert "NMOS_SETTINGS_ADMIN_GROUP" in platform_adapter_source
    assert "NMOS_RUNTIME_DIR" in platform_adapter_source
    assert "NMOS_STATE_DIR" in platform_adapter_source
    assert "PYTHONPATH" not in greeter_launcher_source
    assert "PYTHONPATH" not in settings_launcher_source
    assert "PYTHONPATH" not in control_center_launcher_source
    assert "PYTHONPATH" not in persistence_launcher_source


def test_service_units_include_requested_hardening(repo_root: Path) -> None:
    common_source = (repo_root / "build" / "lib" / "common.sh").read_text(encoding="utf-8")
    settings_service = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-settings.service"
    ).read_text(encoding="utf-8")
    logging_service = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-logging-policy.service"
    ).read_text(encoding="utf-8")
    app_isolation_service = (
        repo_root
        / "config"
        / "system-overlay"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
        / "nmos-app-isolation-policy.service"
    ).read_text(encoding="utf-8")
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

    for service_source in (settings_service, logging_service, app_isolation_service, persistent_service, network_service):
        for value in ("NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=yes", "PrivateTmp=yes"):
            assert value in service_source

    assert "CapabilityBoundingSet=" in settings_service
    assert "ReadWritePaths=@NMOS_RUNTIME_DIR@ @NMOS_STATE_DIR@" in settings_service
    assert "RestrictAddressFamilies=AF_UNIX" in settings_service
    assert "ReadWritePaths=/etc/systemd/journald.conf.d @NMOS_RUNTIME_DIR@" in logging_service
    assert "RestrictAddressFamilies=AF_UNIX" in logging_service
    assert "ReadWritePaths=/var/lib/flatpak/overrides @NMOS_RUNTIME_DIR@" in app_isolation_service
    assert "RestrictAddressFamilies=AF_UNIX" in app_isolation_service

    for value in ("NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=yes", "PrivateTmp=yes"):
        assert value in persistent_service
        assert value in network_service

    assert "CapabilityBoundingSet=" in app_isolation_service
    assert "CapabilityBoundingSet=" in persistent_service
    assert "CapabilityBoundingSet=" in network_service
    assert "ReadWritePaths=@NMOS_RUNTIME_DIR@ @NMOS_STATE_DIR@" in persistent_service
    assert "ReadWritePaths=@NMOS_RUNTIME_DIR@" in network_service
    assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK" in network_service
    assert "render_platform_overlay_templates" in common_source
    assert "nmos-settings.service" in common_source
    assert "nmos-logging-policy.service" in common_source
    assert "nmos-app-isolation-policy.service" in common_source
    assert "nmos-persistent-storage.service" in common_source
    assert "nmos-network-bootstrap.service" in common_source


def test_platform_adapter_templates_rendered_by_build_helpers(repo_root: Path) -> None:
    common_source = (repo_root / "build" / "lib" / "common.sh").read_text(encoding="utf-8")
    settings_policy_source = (
        repo_root / "config" / "system-overlay" / "etc" / "dbus-1" / "system.d" / "org.nmos.Settings1.conf"
    ).read_text(encoding="utf-8")
    persistent_policy_source = (
        repo_root / "config" / "system-overlay" / "etc" / "dbus-1" / "system.d" / "org.nmos.PersistentStorage.conf"
    ).read_text(encoding="utf-8")
    tmpfiles_source = (
        repo_root / "config" / "system-overlay" / "usr" / "lib" / "tmpfiles.d" / "nmos.conf"
    ).read_text(encoding="utf-8")

    assert "render_platform_overlay_templates" in common_source
    assert "resolve_platform_values" in common_source
    assert "@NMOS_GDM_USER@" in settings_policy_source
    assert "@NMOS_SETTINGS_ADMIN_GROUP@" in settings_policy_source
    assert "@NMOS_GDM_USER@" in persistent_policy_source
    assert "@NMOS_RUNTIME_DIR@" in tmpfiles_source
    assert "@NMOS_STATE_DIR@" in tmpfiles_source


def test_workflow_includes_overlay_and_windows_validation(repo_root: Path) -> None:
    workflow_source = (repo_root / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "build-smoke:" in workflow_source
    assert "smoke-overlay.sh" in workflow_source
    assert "verify-installer-media.sh" in workflow_source
    assert "windows-smoke:" in workflow_source
    assert "verify-windows-wsl-bridge.ps1" in workflow_source
    assert "verify-control-center.sh" in workflow_source


def test_settings_service_and_theme_assets_exist(repo_root: Path) -> None:
    settings_service_source = (
        repo_root / "apps" / "nmos_settings" / "nmos_settings" / "service.py"
    ).read_text(encoding="utf-8")
    settings_client_source = (
        repo_root / "apps" / "nmos_common" / "nmos_common" / "settings_client.py"
    ).read_text(encoding="utf-8")
    settings_policy_source = (
        repo_root / "config" / "system-overlay" / "etc" / "dbus-1" / "system.d" / "org.nmos.Settings1.conf"
    ).read_text(encoding="utf-8")
    control_center_source = (
        repo_root / "apps" / "nmos_control_center" / "nmos_control_center" / "main.py"
    ).read_text(encoding="utf-8")
    help_launcher_source = (
        repo_root / "config" / "system-overlay" / "usr" / "local" / "bin" / "nmos-help"
    ).read_text(encoding="utf-8")
    help_desktop_source = (
        repo_root / "config" / "system-overlay" / "usr" / "share" / "applications" / "nmos-help.desktop"
    ).read_text(encoding="utf-8")
    css_source = (
        repo_root / "config" / "system-overlay" / "usr" / "share" / "nmos" / "theme" / "nmos.css"
    ).read_text(encoding="utf-8")
    wallpaper_night = repo_root / "config" / "system-overlay" / "usr" / "share" / "nmos" / "theme" / "wallpaper-night.svg"
    wallpaper_light = repo_root / "config" / "system-overlay" / "usr" / "share" / "nmos" / "theme" / "wallpaper-light.svg"

    assert "DBUS_NAME" in settings_service_source
    assert "DBUS_READ_INTERFACE" in settings_service_source
    assert "DBUS_WRITE_INTERFACE" in settings_service_source
    assert "sender_keyword=\"sender\"" in settings_service_source
    assert "_assert_write_authorized" in settings_service_source
    assert "get_unix_user" in settings_service_source
    assert "get_settings_admin_group" in settings_service_source
    assert "ApplyPreset" in settings_service_source
    assert "SetOverrides" in settings_service_source
    assert "GetPendingRebootChanges" in settings_service_source
    assert "SettingsClient" in settings_client_source
    assert "DBUS_READ_INTERFACE" in settings_client_source
    assert "DBUS_WRITE_INTERFACE" in settings_client_source
    assert "allow_local_fallback=False" in control_center_source
    assert "describe_backend_issue" in control_center_source
    assert "backend_recovery_hint" in control_center_source
    assert "Diagnostics" in control_center_source
    assert "authorized session" in control_center_source
    assert "service health" in control_center_source
    assert "Review mode only until service is reachable. Use Diagnostics for details." in control_center_source
    assert "error.user_message()" in control_center_source
    assert "SettingsClientError" in settings_client_source
    assert "RETRIABLE_DBUS_ERRORS" in settings_client_source
    assert "BACKEND_UNAVAILABLE_DBUS_ERRORS" in settings_client_source
    assert "backend_unavailable" in settings_client_source
    assert "connection failed" in settings_client_source
    assert "denied access" in settings_client_source
    assert "NMOS_ALLOW_LOCAL_SETTINGS_FALLBACK" in settings_client_source
    assert '<deny send_destination="org.nmos.Settings1"/>' in settings_policy_source
    assert '<policy at_console="true">' in settings_policy_source
    assert 'send_interface="org.nmos.Settings1.Read"' in settings_policy_source
    assert 'send_interface="org.nmos.Settings1.Write"' in settings_policy_source
    assert '@NMOS_SETTINGS_ADMIN_GROUP@' in settings_policy_source
    assert "NM-OS Control Center" in control_center_source
    assert "Profiles" in control_center_source
    assert "Appearance" in control_center_source
    assert "default_browser" in control_center_source
    assert "python3 -m nmos_help.main" in help_launcher_source
    assert "Exec=/usr/local/bin/nmos-help" in help_desktop_source
    assert ".nmos-root" in css_source
    assert "theme-nmos-classic" in css_source
    assert wallpaper_night.exists()
    assert wallpaper_light.exists()


def test_installer_media_and_assets_are_packaged(repo_root: Path) -> None:
    build_source = (repo_root / "build" / "build.sh").read_text(encoding="utf-8")
    common_source = (repo_root / "build" / "lib" / "common.sh").read_text(encoding="utf-8")
    verify_artifacts_source = (repo_root / "build" / "verify-artifacts.sh").read_text(encoding="utf-8")
    installer_settings = (
        repo_root / "config" / "installer" / "calamares" / "settings.conf"
    ).read_text(encoding="utf-8")
    branding_source = (
        repo_root / "config" / "installer" / "calamares" / "branding" / "nmos" / "branding.desc"
    ).read_text(encoding="utf-8")
    installer_preseed = (
        repo_root / "config" / "installer" / "debian-installer" / "preseed" / "nmos.cfg.in"
    ).read_text(encoding="utf-8")
    base_iso_lock = (
        repo_root / "config" / "installer" / "base-iso.lock"
    ).read_text(encoding="utf-8")
    late_command_template = (
        repo_root / "config" / "installer" / "debian-installer" / "preseed" / "install-overlay.sh.in"
    ).read_text(encoding="utf-8")
    installer_packages = (
        repo_root / "config" / "installer-packages" / "base.txt"
    ).read_text(encoding="utf-8")

    assert "installer_assets" in build_source
    assert "installer_iso=" in build_source
    assert "build_installer_iso_image" in build_source
    assert "resolve_base_installer_iso" in common_source
    assert "is_truthy" in common_source
    assert "BASE_ISO_LOCK_FILE" in common_source
    assert "read_base_iso_lock_value" in common_source
    assert "NMOS_BASE_INSTALLER_SHA256" in common_source
    assert "NMOS_ALLOW_UNPINNED_BASE_ISO" in common_source
    assert "base ISO lock is incomplete" in common_source
    assert "installer_iso_name" in common_source
    assert "preseed/file=/cdrom/preseed/nmos.cfg" in common_source
    assert 'sub(/^\\.\\//, "", path)' in common_source
    assert 'sub(/^\\*/, "", path)' in common_source
    assert "xorriso -osirrox on -indev" in verify_artifacts_source
    assert "branding: nmos" in installer_settings
    assert "productName: \"NM-OS\"" in branding_source
    assert "@PKGSEL_INCLUDE@" in installer_preseed
    assert "in-target /bin/bash /root/nmos-install-overlay.sh" in installer_preseed
    assert 'tar -xzf "${OVERLAY_ARCHIVE}" -C /' in late_command_template
    assert "ISO_FILE=debian-" in base_iso_lock
    assert "SHA256=" in base_iso_lock
    assert "calamares" in installer_packages
    assert "flatpak" in installer_packages


def test_i18n_supports_spanish_without_extra_locales(repo_root: Path) -> None:
    i18n_source = (repo_root / "apps" / "nmos_common" / "nmos_common" / "i18n.py").read_text(encoding="utf-8")
    assert "es_ES.UTF-8" in i18n_source
    for unsupported_locale in ("tr_TR.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"):
        assert unsupported_locale not in i18n_source
    assert display_language_name("es_ES.UTF-8") == "Espa\u00f1ol"
    assert translate("es_ES.UTF-8", "Security profile") == "Perfil de seguridad"
    assert translate("es_ES.UTF-8", "Theme: {theme}", theme="Se\u00f1al cl\u00e1sica") == "Tema: Se\u00f1al cl\u00e1sica"
    assert translate("es_ES.UTF-8", "NM-OS Setup") == "Configuraci\u00f3n de NM-OS"
    assert translate("es_ES.UTF-8", "Applies now: {changes}", changes="Idioma") == "Se aplica ahora: Idioma"
    assert translate("es_ES.UTF-8", "None") == "Ninguno"
    assert "Ã" not in translate("es_ES.UTF-8", "NM-OS Setup")
    for key, value in TRANSLATIONS.get("es", {}).items():
        assert "Ã" not in key and "Â" not in key and "�" not in key
        assert "Ã" not in value and "Â" not in value and "�" not in value
