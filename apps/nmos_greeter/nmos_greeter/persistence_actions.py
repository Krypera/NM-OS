from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib
from nmos_common.passphrase_policy import evaluate_passphrase


def refresh_persistence(window) -> None:
    if window.persistence_action_in_progress:
        return
    if window.persistence_refresh_in_progress:
        window.persistence_refresh_pending = True
        return
    window.persistence_refresh_in_progress = True
    window.update_persistence_actions(window.persistence_state)
    window.update_navigation()
    thread = threading.Thread(target=window.run_persistence_refresh_worker, daemon=True)
    thread.start()


def run_persistence_refresh_worker(window) -> None:
    try:
        client = window.persistence_client_factory()
        state = client.get_state()
        GLib.idle_add(window.complete_persistence_refresh, dict(state), "")
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        GLib.idle_add(window.complete_persistence_refresh, None, str(exc))


def complete_persistence_refresh(window, state: dict | None, error: str) -> bool:
    window.persistence_refresh_in_progress = False
    if error:
        window.persistence_state = {}
        window.persistence_init_error = error
        window.persistence_label.set_text(
            window.tr("Encrypted vault backend unavailable: {error}", error=window.translate_message(error))
        )
        window.update_persistence_actions({})
        window.update_navigation()
    elif state is not None:
        window.persistence_state = dict(state)
        window.persistence_init_error = ""
        window.persistence_label.set_text(window.render_persistence_state(state))
        window.update_persistence_actions(state)
        window.update_navigation()

    if window.persistence_refresh_pending and not window.persistence_action_in_progress:
        window.persistence_refresh_pending = False
        window.refresh_persistence()
    return GLib.SOURCE_REMOVE


def render_persistence_state(window, state: dict) -> str:
    created = state.get("created", False)
    unlocked = state.get("unlocked", False)
    busy = state.get("busy", False)
    can_create = state.get("can_create", False)
    reason = state.get("reason", "")
    vault_path = state.get("path", "")
    last_error = state.get("last_error", "")
    vault_label = vault_path or window.tr("the encrypted vault")
    if last_error:
        return window.tr("Encrypted vault error: {error}", error=window.translate_message(str(last_error)))
    if busy:
        return window.tr("Encrypted vault activity is in progress.")
    if created and unlocked:
        return window.tr("Encrypted vault is unlocked and ready.")
    if created:
        return window.tr("Encrypted vault exists at {path} and can be unlocked.", path=vault_label)
    if reason == "no_space":
        return window.tr("Encrypted vault cannot be created because the system disk does not have enough free space.")
    if can_create:
        return window.tr("Encrypted vault can be created at {path}.", path=vault_label)
    if reason == "already_exists":
        return window.tr("Encrypted vault already exists at {path}.", path=vault_label)
    return window.tr("Encrypted vault state is unavailable.")


def update_persistence_actions(window, state: dict) -> None:
    created = bool(state.get("created"))
    unlocked = bool(state.get("unlocked"))
    busy = bool(state.get("busy")) or window.persistence_action_in_progress or window.persistence_refresh_in_progress
    can_create = bool(state.get("can_create"))
    window.persistence_create.set_sensitive(can_create and not busy)
    window.persistence_unlock.set_sensitive(created and not unlocked and not busy)
    window.persistence_lock.set_sensitive(unlocked and not busy)
    window.persistence_repair.set_sensitive(created and unlocked and not busy)


def on_create_persistence(window, _button) -> None:
    passphrase = window.persistence_password.get_text()
    window.persistence_password.set_text("")
    evaluation = evaluate_passphrase(passphrase)
    if not evaluation["valid_for_creation"]:
        issues = ", ".join(str(item) for item in evaluation["issues"])
        window.set_status(f"Vault passphrase is too weak. Missing: {issues}")
        return
    window.start_persistence_action("create", passphrase)


def on_unlock_persistence(window, _button) -> None:
    passphrase = window.persistence_password.get_text()
    window.persistence_password.set_text("")
    window.start_persistence_action("unlock", passphrase)


def on_lock_persistence(window, _button) -> None:
    window.start_persistence_action("lock")


def on_repair_persistence(window, _button) -> None:
    window.start_persistence_action("repair")


def start_persistence_action(window, action: str, passphrase: str | None = None) -> None:
    if window.persistence_action_in_progress:
        window.set_status(
            window.tr(
                "Encrypted vault action {action} is still running. Please wait.",
                action=window.action_label(window.persistence_action_name),
            )
        )
        return
    if window.persistence_refresh_in_progress:
        window.set_status(window.tr("Encrypted vault status is refreshing. Please wait."))
        window.persistence_refresh_pending = True
        return

    window.persistence_action_in_progress = True
    window.persistence_action_name = action
    busy_state = dict(window.persistence_state)
    busy_state["busy"] = True
    window.persistence_state = busy_state
    window.persistence_label.set_text(
        window.tr("Encrypted vault action {action} is in progress...", action=window.action_label(action))
    )
    window.update_persistence_actions(busy_state)
    window.update_navigation()
    window.set_status(window.tr("Starting encrypted vault action {action}...", action=window.action_label(action)))
    thread = threading.Thread(
        target=window.run_persistence_action_worker,
        args=(action, passphrase),
        daemon=True,
    )
    thread.start()


def run_persistence_action_worker(window, action: str, passphrase: str | None) -> None:
    try:
        client = window.persistence_client_factory()
        actions = {
            "create": lambda: client.create(passphrase or ""),
            "unlock": lambda: client.unlock(passphrase or ""),
            "lock": client.lock,
            "repair": client.repair,
        }
        if action not in actions:
            raise ValueError(f"unsupported persistence action: {action}")
        response = actions[action]()
        GLib.idle_add(window.complete_persistence_action, action, dict(response), "")
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        GLib.idle_add(window.complete_persistence_action, action, None, str(exc))


def complete_persistence_action(window, action: str, response: dict | None, error: str) -> bool:
    window.persistence_action_in_progress = False
    window.persistence_action_name = ""
    if error:
        window.set_status(
            window.tr(
                "Encrypted vault action {action} failed: {error}",
                action=window.action_label(action),
                error=window.translate_message(error),
            )
        )
        window.refresh_persistence()
        return GLib.SOURCE_REMOVE
    if response is not None:
        window.handle_persistence_response(action, response)
    else:
        window.refresh_persistence()
    return GLib.SOURCE_REMOVE


def handle_persistence_response(window, action: str, response: dict) -> None:
    window.persistence_state = dict(response)
    window.persistence_label.set_text(window.render_persistence_state(response))
    window.update_persistence_actions(response)
    window.update_navigation()
    if response.get("last_error"):
        window.set_status(
            window.tr(
                "Encrypted vault action {action} failed: {error}",
                action=window.action_label(action),
                error=window.translate_message(str(response["last_error"])),
            )
        )
        return
    window.set_status(
        window.tr("Encrypted vault action {action} completed.", action=window.action_label(action))
    )
