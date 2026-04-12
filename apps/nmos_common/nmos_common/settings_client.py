from __future__ import annotations

import os

from nmos_common.config_helpers import parse_bool
from nmos_common.system_settings import (
    apply_system_profile,
    commit_system_settings,
    load_effective_system_settings,
    load_system_settings,
    reset_to_preset,
    update_system_overrides,
)

DBUS_NAME = "org.nmos.Settings1"
DBUS_PATH = "/org/nmos/Settings1"
DBUS_INTERFACE = "org.nmos.Settings1"


def load_dbus():
    import dbus

    return dbus


RETRIABLE_DBUS_ERRORS = {
    "org.freedesktop.DBus.Error.ServiceUnknown",
    "org.freedesktop.DBus.Error.NoReply",
    "org.freedesktop.DBus.Error.Disconnected",
    "org.freedesktop.DBus.Error.TimedOut",
}


class SettingsClientError(RuntimeError):
    def __init__(self, method_name: str, reason: str, *, dbus_name: str = "") -> None:
        self.method_name = method_name
        self.reason = reason
        self.dbus_name = dbus_name
        super().__init__(f"{method_name} failed: {reason}")

    def user_message(self) -> str:
        if self.reason == "access_denied":
            return "Settings backend denied access to this session."
        if self.reason == "backend_unavailable":
            return "Settings backend is unavailable right now."
        if self.reason == "transport_error":
            return "Settings backend connection failed."
        if self.reason == "dbus_import_error":
            return "D-Bus bindings are unavailable on this system."
        return "Settings backend request failed."


class LocalSettingsClient:
    def get_settings(self) -> dict:
        return load_system_settings()

    def get_effective_settings(self) -> dict:
        return load_effective_system_settings()

    def apply_preset(self, profile: str) -> dict:
        return apply_system_profile(profile)

    def set_overrides(self, overrides: dict) -> dict:
        return update_system_overrides(overrides)

    def reset_to_preset(self) -> dict:
        return reset_to_preset()

    def get_pending_reboot_changes(self) -> list[str]:
        return list(load_system_settings().get("pending_reboot", []))

    def commit(self) -> dict:
        return commit_system_settings()


class SettingsClient:
    def __init__(self, *, allow_local_fallback: bool | None = None) -> None:
        if allow_local_fallback is None:
            allow_local_fallback = parse_bool(os.environ.get("NMOS_ALLOW_LOCAL_SETTINGS_FALLBACK"), default=False)
        self.allow_local_fallback = bool(allow_local_fallback)
        self.local = LocalSettingsClient()

    def _interface(self):
        dbus = load_dbus()
        bus = dbus.SystemBus()
        proxy = bus.get_object(DBUS_NAME, DBUS_PATH, introspect=False)
        return dbus.Interface(proxy, DBUS_INTERFACE)

    def _with_fallback(self, method_name: str, local_method, *args):
        try:
            interface = self._interface()
            response = getattr(interface, method_name)(*args)
        except Exception as error:
            reason = self._classify_error_reason(error)
            if self.allow_local_fallback and self._can_use_local_fallback(error):
                return local_method(*args)
            raise SettingsClientError(
                method_name,
                reason,
                dbus_name=self._dbus_error_name(error),
            ) from error
        if method_name == "GetPendingRebootChanges":
            return [str(item) for item in response]
        return dict(response)

    def _dbus_error_name(self, error: Exception) -> str:
        get_name = getattr(error, "get_dbus_name", None)
        if callable(get_name):
            try:
                return str(get_name())
            except Exception:
                return ""
        return ""

    def _classify_error_reason(self, error: Exception) -> str:
        if isinstance(error, ImportError):
            return "dbus_import_error"
        dbus_name = self._dbus_error_name(error)
        if dbus_name == "org.freedesktop.DBus.Error.AccessDenied":
            return "access_denied"
        if dbus_name in RETRIABLE_DBUS_ERRORS:
            return "transport_error"
        if dbus_name == "org.freedesktop.DBus.Error.ServiceUnknown":
            return "backend_unavailable"
        if dbus_name:
            return "dbus_error"
        return "unexpected_error"

    def _can_use_local_fallback(self, error: Exception) -> bool:
        if isinstance(error, ImportError):
            return True
        get_name = getattr(error, "get_dbus_name", None)
        if callable(get_name):
            try:
                name = str(get_name())
            except Exception:
                return False
            return name in RETRIABLE_DBUS_ERRORS
        return False

    def get_settings(self) -> dict:
        return self._with_fallback("GetSettings", self.local.get_settings)

    def get_effective_settings(self) -> dict:
        return self._with_fallback("GetEffectiveSettings", self.local.get_effective_settings)

    def apply_preset(self, profile: str) -> dict:
        return self._with_fallback("ApplyPreset", self.local.apply_preset, profile)

    def set_overrides(self, overrides: dict) -> dict:
        return self._with_fallback("SetOverrides", self.local.set_overrides, overrides)

    def reset_to_preset(self) -> dict:
        return self._with_fallback("ResetToPreset", self.local.reset_to_preset)

    def get_pending_reboot_changes(self) -> list[str]:
        return self._with_fallback("GetPendingRebootChanges", self.local.get_pending_reboot_changes)

    def commit(self) -> dict:
        return self._with_fallback("Commit", self.local.commit)
