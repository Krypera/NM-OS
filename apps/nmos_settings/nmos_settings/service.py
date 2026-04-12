from __future__ import annotations

import logging

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
from nmos_common.settings_client import (
    DBUS_NAME,
    DBUS_PATH,
    DBUS_READ_INTERFACE,
    DBUS_WRITE_INTERFACE,
)
from nmos_common.system_settings import (
    apply_system_profile,
    commit_system_settings,
    extract_effective_settings,
    load_system_settings,
    reset_to_preset,
    update_system_overrides,
)

LOGGER = logging.getLogger("nmos.settings.service")


class SettingsService(dbus.service.Object):
    def __init__(self, bus: dbus.SystemBus) -> None:
        name = dbus.service.BusName(DBUS_NAME, bus)
        super().__init__(name, DBUS_PATH)

    def _notify(self, settings: dict) -> dict:
        self.SettingsChanged(dict(settings))
        return settings

    @dbus.service.signal(DBUS_WRITE_INTERFACE, signature="a{sv}")
    def SettingsChanged(self, settings: dict) -> None:
        return None

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetSettings(self) -> dict:
        return load_system_settings()

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetEffectiveSettings(self) -> dict:
        return extract_effective_settings(load_system_settings())

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="s", out_signature="a{sv}")
    def ApplyPreset(self, profile: str) -> dict:
        settings = apply_system_profile(profile)
        return self._notify(settings)

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="a{sv}", out_signature="a{sv}")
    def SetOverrides(self, overrides: dict) -> dict:
        settings = update_system_overrides(dict(overrides))
        return self._notify(settings)

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="", out_signature="a{sv}")
    def ResetToPreset(self) -> dict:
        settings = reset_to_preset()
        return self._notify(settings)

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="as")
    def GetPendingRebootChanges(self) -> list[str]:
        return list(load_system_settings().get("pending_reboot", []))

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="", out_signature="a{sv}")
    def Commit(self) -> dict:
        settings = commit_system_settings()
        return self._notify(settings)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    SettingsService(bus)
    LOGGER.info("NM-OS settings service ready")
    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
