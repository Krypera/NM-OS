from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib

from nmos_greeter.client import read_network_status


def default_network_status(_window) -> dict:
    return {
        "ready": False,
        "progress": 0,
        "phase": "bootstrap",
        "summary": "Waiting for Tor",
        "last_error": "",
        "updated_at": "",
    }


def refresh_network(window, *, force_status: bool = False) -> None:
    try:
        status = read_network_status()
    except (OSError, ValueError, RuntimeError) as exc:
        status = {
            "ready": False,
            "progress": 0,
            "phase": "failed",
            "summary": "Unable to read network status",
            "last_error": str(exc),
            "updated_at": "",
        }

    window.network_status = status
    summary = window.translate_message(str(status["summary"]))
    window.network_label.set_text(f"{summary} ({status['progress']}%)")
    window.network_progress.set_fraction(status["progress"] / 100.0)

    phase = str(status.get("phase", "bootstrap"))
    if status.get("last_error"):
        window.set_status(
            window.tr("Network status: {error}", error=window.translate_message(str(status["last_error"]))),
            source="network",
            force=force_status,
        )
    elif phase == "disabled":
        window.set_status(window.tr("Networking is currently disabled."), source="network", force=force_status)
    elif phase == "open":
        window.set_status(window.tr("Direct network access is enabled."), source="network", force=force_status)
    elif status["ready"]:
        window.set_status(window.tr("Tor connection is ready."), source="network", force=force_status)
    else:
        window.set_status(window.tr("Waiting for Tor to become ready."), source="network", force=force_status)
    window.update_navigation()


def setup_network_watchers(window) -> None:
    for path in ("/run/nmos/network-status.json", "/run/nmos/network-ready"):
        file_obj = Gio.File.new_for_path(path)
        monitor = None
        try:
            monitor = file_obj.monitor_file(Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error:
            parent = file_obj.get_parent()
            if parent is not None:
                try:
                    monitor = parent.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                except GLib.Error:
                    monitor = None
        if monitor is None:
            continue
        monitor.connect("changed", window.on_network_file_changed)
        window.network_monitors.append(monitor)


def on_network_file_changed(window, _monitor, _file, _other_file, event_type) -> None:
    if event_type not in {
        Gio.FileMonitorEvent.CREATED,
        Gio.FileMonitorEvent.CHANGED,
        Gio.FileMonitorEvent.CHANGES_DONE_HINT,
        Gio.FileMonitorEvent.DELETED,
        Gio.FileMonitorEvent.MOVED_IN,
        Gio.FileMonitorEvent.MOVED_OUT,
    }:
        return
    changed_names = set()
    if _file is not None:
        changed_names.add(_file.get_basename())
    if _other_file is not None:
        changed_names.add(_other_file.get_basename())
    if changed_names and not changed_names.intersection({"network-status.json", "network-ready"}):
        return
    queue_network_refresh(window)


def queue_network_refresh(window, *, force_status: bool = False) -> None:
    window.network_refresh_force = window.network_refresh_force or force_status
    if window.network_refresh_pending_id:
        return
    window.network_refresh_pending_id = GLib.timeout_add(200, window.run_queued_network_refresh)


def run_queued_network_refresh(window) -> bool:
    window.network_refresh_pending_id = 0
    force_status = window.network_refresh_force
    window.network_refresh_force = False
    window.refresh_network(force_status=force_status)
    return GLib.SOURCE_REMOVE
