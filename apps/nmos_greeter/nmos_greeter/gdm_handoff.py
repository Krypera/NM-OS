from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib


def on_finish(window, _button) -> None:
    if not window.can_finish():
        window.set_status(window.tr("Session is not ready yet."))
        return
    try:
        window.state = window.collect_state()
        window.save_state(window.state)
    except (OSError, ValueError, RuntimeError) as exc:
        window.logger.error("failed to save greeter state: %s", exc)
        window.set_status(window.tr("Failed to save greeter state: {error}", error=window.tr("internal error")))
        return
    if window.gdm_client is None:
        if window.gdm_init_error:
            window.logger.error("gdm client is unavailable: %s", window.gdm_init_error)
            window.set_status(window.tr("GDM session control is unavailable: {error}", error=window.tr("internal error")))
        else:
            window.set_status(window.tr("Greeter state saved, but GDM session control is unavailable."))
        return
    window.session_start_in_progress = True
    window.set_sensitive(False)
    window.set_status(window.tr("Starting the live session..."))
    window.arm_session_start_timeout()
    try:
        window.gdm_client.start_session()
    except (OSError, ValueError, RuntimeError) as exc:
        window.logger.error("failed to start GDM live session: %s", exc)
        window.session_start_in_progress = False
        window.clear_session_start_timeout()
        window.set_sensitive(True)
        window.set_status(window.tr("Failed to start the live session: {error}", error=window.tr("internal error")))


def arm_session_start_timeout(window) -> None:
    window.clear_session_start_timeout()
    window.session_start_timeout_id = GLib.timeout_add_seconds(15, window.on_session_start_timeout)


def clear_session_start_timeout(window) -> None:
    if window.session_start_timeout_id:
        GLib.source_remove(window.session_start_timeout_id)
        window.session_start_timeout_id = 0


def on_session_start_timeout(window) -> bool:
    window.session_start_timeout_id = 0
    window.session_start_in_progress = False
    cancel_error = ""
    if window.gdm_client is not None:
        try:
            window.gdm_client.cancel_pending_login()
        except (OSError, RuntimeError, ValueError) as exc:
            cancel_error = str(exc)
    window.set_sensitive(True)
    if cancel_error:
        window.logger.error("live session timeout reset failed: %s", cancel_error)
        window.set_status(window.tr("Live session start timed out. Login flow reset failed: {error}", error=window.tr("internal error")))
    else:
        window.set_status(window.tr("Live session start timed out. Login flow was reset."))
    return GLib.SOURCE_REMOVE


def on_session_opened(window) -> None:
    window.session_start_in_progress = False
    window.clear_session_start_timeout()
    window.close()


def on_session_problem(window, problem: str) -> None:
    window.session_start_in_progress = False
    window.clear_session_start_timeout()
    if window.gdm_client is not None:
        try:
            window.gdm_client.cancel_pending_login()
        except (OSError, RuntimeError, ValueError) as exc:
            window.logger.error("failed to cancel pending login after session problem: %s", exc)
    window.set_sensitive(True)
    window.logger.error("live session problem from gdm: %s", problem)
    window.set_status(window.tr("Live session start failed: {problem}", problem=window.tr("internal error")))
