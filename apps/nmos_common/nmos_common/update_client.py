from __future__ import annotations

import os

from nmos_common.config_helpers import parse_bool
from nmos_common.update_engine import (
    UpdateEngineError,
    acknowledge_healthy_boot,
    check_for_updates,
    commit_staged_update,
    get_channels,
    get_history,
    get_status,
    rollback_to_previous_slot,
    stage_update,
)

DBUS_NAME = "org.nmos.Update1"
DBUS_PATH = "/org/nmos/Update1"
DBUS_READ_INTERFACE = "org.nmos.Update1.Read"
DBUS_WRITE_INTERFACE = "org.nmos.Update1.Write"


def load_dbus():
    import dbus

    return dbus


RETRIABLE_DBUS_ERRORS = {
    "org.freedesktop.DBus.Error.NoReply",
    "org.freedesktop.DBus.Error.Disconnected",
    "org.freedesktop.DBus.Error.TimedOut",
}

BACKEND_UNAVAILABLE_DBUS_ERRORS = {
    "org.freedesktop.DBus.Error.ServiceUnknown",
    "org.freedesktop.DBus.Error.NameHasNoOwner",
}


class UpdateClientError(RuntimeError):
    def __init__(self, method_name: str, reason: str, *, dbus_name: str = "") -> None:
        self.method_name = method_name
        self.reason = reason
        self.dbus_name = dbus_name
        super().__init__(f"{method_name} failed: {reason}")

    def user_message(self) -> str:
        if self.reason == "access_denied":
            return "Update backend denied access to this session."
        if self.reason == "backend_unavailable":
            return "Update backend is unavailable right now."
        if self.reason == "transport_error":
            return "Update backend connection failed."
        if self.reason == "dbus_import_error":
            return "D-Bus bindings are unavailable on this system."
        return "Update backend request failed."


class LocalUpdateClient:
    def get_status(self) -> dict:
        return get_status()

    def get_history(self) -> list[dict]:
        return get_history()

    def get_channels(self) -> dict:
        return get_channels()

    def check_for_updates(self, channel: str) -> dict:
        return check_for_updates(channel)

    def stage_update(self, channel: str) -> dict:
        return stage_update(channel)

    def commit_staged_update(self) -> dict:
        return commit_staged_update()

    def rollback_to_previous_slot(self) -> dict:
        return rollback_to_previous_slot()

    def acknowledge_healthy_boot(self) -> dict:
        return acknowledge_healthy_boot()


class UpdateClient:
    def __init__(self, *, allow_local_fallback: bool | None = None) -> None:
        if allow_local_fallback is None:
            allow_local_fallback = parse_bool(os.environ.get("NMOS_ALLOW_LOCAL_UPDATE_FALLBACK"), default=False)
        self.allow_local_fallback = bool(allow_local_fallback)
        self.local = LocalUpdateClient()

    def _interface(self, dbus_interface: str):
        dbus = load_dbus()
        bus = dbus.SystemBus()
        proxy = bus.get_object(DBUS_NAME, DBUS_PATH, introspect=False)
        return dbus.Interface(proxy, dbus_interface)

    def _with_fallback(self, method_name: str, dbus_interface: str, local_method, *args):
        try:
            interface = self._interface(dbus_interface)
            response = getattr(interface, method_name)(*args)
        except Exception as error:
            reason = self._classify_error_reason(error)
            if self.allow_local_fallback and self._can_use_local_fallback(error):
                try:
                    return local_method(*args)
                except UpdateEngineError as inner_error:
                    raise UpdateClientError(method_name, inner_error.reason) from inner_error
            raise UpdateClientError(method_name, reason, dbus_name=self._dbus_error_name(error)) from error
        if method_name in {"GetHistory"}:
            return [dict(item) for item in response]
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
        if dbus_name in BACKEND_UNAVAILABLE_DBUS_ERRORS:
            return "backend_unavailable"
        if dbus_name == "org.freedesktop.DBus.Error.AccessDenied":
            return "access_denied"
        if dbus_name in RETRIABLE_DBUS_ERRORS:
            return "transport_error"
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
            return name in RETRIABLE_DBUS_ERRORS or name in BACKEND_UNAVAILABLE_DBUS_ERRORS
        return False

    def get_status(self) -> dict:
        return self._with_fallback("GetStatus", DBUS_READ_INTERFACE, self.local.get_status)

    def get_history(self) -> list[dict]:
        return self._with_fallback("GetHistory", DBUS_READ_INTERFACE, self.local.get_history)

    def get_channels(self) -> dict:
        return self._with_fallback("GetChannels", DBUS_READ_INTERFACE, self.local.get_channels)

    def check_for_updates(self, channel: str) -> dict:
        return self._with_fallback("CheckForUpdates", DBUS_WRITE_INTERFACE, self.local.check_for_updates, channel)

    def stage_update(self, channel: str) -> dict:
        return self._with_fallback("StageUpdate", DBUS_WRITE_INTERFACE, self.local.stage_update, channel)

    def commit_staged_update(self) -> dict:
        return self._with_fallback("CommitStagedUpdate", DBUS_WRITE_INTERFACE, self.local.commit_staged_update)

    def rollback_to_previous_slot(self) -> dict:
        return self._with_fallback(
            "RollbackToPreviousSlot",
            DBUS_WRITE_INTERFACE,
            self.local.rollback_to_previous_slot,
        )

    def acknowledge_healthy_boot(self) -> dict:
        return self._with_fallback(
            "AcknowledgeHealthyBoot",
            DBUS_WRITE_INTERFACE,
            self.local.acknowledge_healthy_boot,
        )

    def connect_update_state_changed(self, handler):
        try:
            dbus = load_dbus()
            bus = dbus.SystemBus()
            proxy = bus.get_object(DBUS_NAME, DBUS_PATH, introspect=False)
            interface = dbus.Interface(proxy, DBUS_WRITE_INTERFACE)
            match = interface.connect_to_signal("UpdateStateChanged", handler)
        except Exception as error:
            raise UpdateClientError(
                "ConnectUpdateStateChanged",
                self._classify_error_reason(error),
                dbus_name=self._dbus_error_name(error),
            ) from error
        return bus, interface, match
