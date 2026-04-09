from __future__ import annotations

import json
import subprocess

import dbus


DBUS_NAME = "org.nmos.PersistentStorage"
DBUS_PATH = "/org/nmos/PersistentStorage"
DBUS_INTERFACE = "org.nmos.PersistentStorage"


class PersistenceClient:
    def __init__(self) -> None:
        self.bus = dbus.SystemBus()
        self.proxy = self.bus.get_object(DBUS_NAME, DBUS_PATH)
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
    proc = subprocess.run(
        ["/usr/local/lib/nmos/tor_bootstrap_status.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)

