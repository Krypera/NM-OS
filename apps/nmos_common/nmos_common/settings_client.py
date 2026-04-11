from __future__ import annotations

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
    def __init__(self, *, allow_local_fallback: bool = True) -> None:
        self.allow_local_fallback = allow_local_fallback
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
        except Exception:
            if not self.allow_local_fallback:
                raise
            return local_method(*args)
        if method_name == "GetPendingRebootChanges":
            return [str(item) for item in response]
        return dict(response)

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
