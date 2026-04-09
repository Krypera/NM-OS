from __future__ import annotations

import json
import subprocess


DBUS_NAME = "org.nmos.PersistentStorage"
DBUS_PATH = "/org/nmos/PersistentStorage"
DBUS_INTERFACE = "org.nmos.PersistentStorage"


def load_dbus():
    import dbus

    return dbus


def normalize_network_status(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {"ready": False, "progress": 0, "summary": "Waiting for Tor bootstrap", "last_error": "invalid status payload"}

    ready_value = raw.get("ready", False)
    if isinstance(ready_value, bool):
        ready = ready_value
    elif isinstance(ready_value, (int, float)):
        ready = ready_value != 0
    elif isinstance(ready_value, str):
        ready = ready_value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        ready = False
    summary = str(raw.get("summary", "Waiting for Tor bootstrap") or "Waiting for Tor bootstrap")
    last_error = str(raw.get("last_error", "") or "")
    try:
        progress = int(raw.get("progress", 0))
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))
    return {
        "ready": ready,
        "progress": progress,
        "summary": summary,
        "last_error": last_error,
    }


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
    proc = subprocess.run(
        ["/usr/local/lib/nmos/tor_bootstrap_status.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return normalize_network_status(json.loads(proc.stdout))
