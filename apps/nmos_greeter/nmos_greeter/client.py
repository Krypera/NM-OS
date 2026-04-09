from __future__ import annotations

import json
from pathlib import Path

from nmos_common.boot_mode import BOOT_MODE_FILE, load_boot_mode_profile
from nmos_common.network_status import normalize_network_status

DBUS_NAME = "org.nmos.PersistentStorage"
DBUS_PATH = "/org/nmos/PersistentStorage"
DBUS_INTERFACE = "org.nmos.PersistentStorage"
NETWORK_READY_FILE = Path("/run/nmos/network-ready")
NETWORK_STATUS_FILE = Path("/run/nmos/network-status.json")


def load_dbus():
    import dbus

    return dbus


class PersistenceClient:
    def _interface(self):
        dbus = load_dbus()
        bus = dbus.SystemBus()
        # Use explicit interface calls without runtime introspection so the
        # greeter can operate with a narrow D-Bus policy.
        proxy = bus.get_object(DBUS_NAME, DBUS_PATH, introspect=False)
        return dbus.Interface(proxy, DBUS_INTERFACE)

    def _call(self, method_name: str, *args):
        interface = self._interface()
        return dict(getattr(interface, method_name)(*args))

    def get_state(self) -> dict:
        return self._call("GetState")

    def create(self, passphrase: str) -> dict:
        return self._call("Create", passphrase)

    def unlock(self, passphrase: str) -> dict:
        return self._call("Unlock", passphrase)

    def lock(self) -> dict:
        return self._call("Lock")

    def repair(self) -> dict:
        return self._call("Repair")


def read_network_status() -> dict:
    if NETWORK_READY_FILE.exists():
        return normalize_network_status(
            {
                "ready": True,
                "progress": 100,
                "phase": "ready",
                "summary": "Tor is ready",
                "last_error": "",
            }
        )

    if NETWORK_STATUS_FILE.exists():
        try:
            return normalize_network_status(json.loads(NETWORK_STATUS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            return normalize_network_status({"last_error": str(exc)})

    return normalize_network_status({})


def read_boot_mode_profile() -> dict:
    return load_boot_mode_profile(BOOT_MODE_FILE)
