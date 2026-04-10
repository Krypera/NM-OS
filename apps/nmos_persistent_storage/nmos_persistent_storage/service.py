from __future__ import annotations

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

from nmos_persistent_storage import DBUS_INTERFACE, DBUS_NAME, DBUS_PATH
from nmos_persistent_storage.storage import PersistentStorageManager, StorageError


class PersistentStorageService(dbus.service.Object):
    def __init__(self, bus: dbus.SystemBus) -> None:
        self.manager = PersistentStorageManager()
        name = dbus.service.BusName(DBUS_NAME, bus)
        super().__init__(name, DBUS_PATH)

    def safe_call(self, callback, *args) -> dict:
        try:
            return callback(*args)
        except StorageError as exc:
            self.manager.set_last_error(str(exc), reason=exc.reason)
            return self.manager.get_state(include_cached_error=True)
        except Exception as exc:
            self.manager.set_last_error(str(exc))
            return self.manager.get_state(include_cached_error=True)

    @dbus.service.method(DBUS_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetState(self) -> dict:
        return self.manager.get_state()

    @dbus.service.method(DBUS_INTERFACE, in_signature="s", out_signature="a{sv}")
    def Create(self, passphrase: str) -> dict:
        return self.safe_call(self.manager.create, passphrase)

    @dbus.service.method(DBUS_INTERFACE, in_signature="s", out_signature="a{sv}")
    def Unlock(self, passphrase: str) -> dict:
        return self.safe_call(self.manager.unlock, passphrase)

    @dbus.service.method(DBUS_INTERFACE, in_signature="", out_signature="a{sv}")
    def Lock(self) -> dict:
        return self.safe_call(self.manager.lock)

    @dbus.service.method(DBUS_INTERFACE, in_signature="", out_signature="a{sv}")
    def Repair(self) -> dict:
        return self.safe_call(self.manager.repair)


def main() -> None:
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    PersistentStorageService(bus)
    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
