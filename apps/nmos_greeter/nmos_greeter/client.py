from __future__ import annotations

import json
from pathlib import Path

from nmos_greeter.network_status import normalize_network_status, parse_bootstrap_status

DBUS_NAME = "org.nmos.PersistentStorage"
DBUS_PATH = "/org/nmos/PersistentStorage"
DBUS_INTERFACE = "org.nmos.PersistentStorage"
NETWORK_READY_FILE = Path("/run/nmos/network-ready")
NETWORK_STATUS_FILE = Path("/run/nmos/network-status.json")


def load_dbus():
    import dbus

    return dbus


class PersistenceClient:
    def __init__(self) -> None:
        dbus = load_dbus()
        self.bus = dbus.SystemBus()
        # Use explicit interface calls without runtime introspection so the
        # greeter can operate with a narrow D-Bus policy.
        self.proxy = self.bus.get_object(DBUS_NAME, DBUS_PATH, introspect=False)
        self.interface = dbus.Interface(self.proxy, DBUS_INTERFACE)

    def get_state(self) -> dict:
        return dict(self.interface.GetState())

    def create(self, passphrase: str) -> dict:
        return dict(self.interface.Create(passphrase))

    def unlock(self, passphrase: str) -> dict:
        return dict(self.interface.Unlock(passphrase))

    def lock(self) -> dict:
        return dict(self.interface.Lock())

    def repair(self) -> dict:
        return dict(self.interface.Repair())


def read_network_status() -> dict:
    if NETWORK_READY_FILE.exists():
        return {"ready": True, "progress": 100, "summary": "Tor is ready", "last_error": ""}

    if NETWORK_STATUS_FILE.exists():
        try:
            return normalize_network_status(json.loads(NETWORK_STATUS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            return normalize_network_status({"last_error": str(exc)})

    return normalize_network_status({})
