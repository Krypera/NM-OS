from __future__ import annotations

import logging
import shutil
import subprocess

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
from nmos_common.platform_adapter import get_gdm_user, get_settings_admin_group
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

from nmos_settings.authorization import build_write_uid_allowlist, is_write_authorized

LOGGER = logging.getLogger("nmos.settings.service")
POLKIT_ACTION_ID = "org.nmos.settings.write"


class SettingsService(dbus.service.Object):
    def __init__(self, bus: dbus.SystemBus) -> None:
        self._bus = bus
        self._write_allowed_uids = build_write_uid_allowlist(get_gdm_user(), get_settings_admin_group())
        name = dbus.service.BusName(DBUS_NAME, bus)
        super().__init__(name, DBUS_PATH)

    def _notify(self, settings: dict) -> dict:
        self.SettingsChanged(dict(settings))
        return settings

    def _assert_write_authorized(self, sender: str | None) -> None:
        if not sender:
            raise dbus.exceptions.DBusException(
                "org.freedesktop.DBus.Error.AccessDenied",
                "missing sender identity for write operation",
            )
        sender_uid = int(self._bus.get_unix_user(sender))
        if is_write_authorized(sender_uid, self._write_allowed_uids):
            return
        if self._is_polkit_write_authorized(sender=sender, sender_uid=sender_uid):
            return
        raise dbus.exceptions.DBusException(
            "org.freedesktop.DBus.Error.AccessDenied",
            "write access denied for this caller",
        )

    def _is_polkit_write_authorized(self, *, sender: str, sender_uid: int) -> bool:
        if shutil.which("pkcheck") is None:
            return False
        try:
            sender_pid = int(self._bus.get_unix_process_id(sender))
        except Exception:
            return False
        try:
            completed = subprocess.run(
                [
                    "pkcheck",
                    "--action-id",
                    POLKIT_ACTION_ID,
                    "--process",
                    str(sender_pid),
                    "--allow-user-interaction",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if completed.returncode == 0:
            LOGGER.info("Polkit authorized settings write for uid=%s pid=%s", sender_uid, sender_pid)
            return True
        LOGGER.warning(
            "Polkit denied settings write for uid=%s pid=%s returncode=%s stderr=%s",
            sender_uid,
            sender_pid,
            completed.returncode,
            (completed.stderr or "").strip(),
        )
        return False

    @dbus.service.signal(DBUS_WRITE_INTERFACE, signature="a{sv}")
    def SettingsChanged(self, settings: dict) -> None:
        return None

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetSettings(self) -> dict:
        return load_system_settings()

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetEffectiveSettings(self) -> dict:
        return extract_effective_settings(load_system_settings())

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="s", out_signature="a{sv}", sender_keyword="sender")
    def ApplyPreset(self, profile: str, sender: str | None = None) -> dict:
        self._assert_write_authorized(sender)
        settings = apply_system_profile(profile)
        return self._notify(settings)

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="a{sv}", out_signature="a{sv}", sender_keyword="sender")
    def SetOverrides(self, overrides: dict, sender: str | None = None) -> dict:
        self._assert_write_authorized(sender)
        settings = update_system_overrides(dict(overrides))
        return self._notify(settings)

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="", out_signature="a{sv}", sender_keyword="sender")
    def ResetToPreset(self, sender: str | None = None) -> dict:
        self._assert_write_authorized(sender)
        settings = reset_to_preset()
        return self._notify(settings)

    @dbus.service.method(DBUS_READ_INTERFACE, in_signature="", out_signature="as")
    def GetPendingRebootChanges(self) -> list[str]:
        return list(load_system_settings().get("pending_reboot", []))

    @dbus.service.method(DBUS_WRITE_INTERFACE, in_signature="", out_signature="a{sv}", sender_keyword="sender")
    def Commit(self, sender: str | None = None) -> dict:
        self._assert_write_authorized(sender)
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
