from __future__ import annotations

import logging
import os

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gio, Gtk

from nmos_common.i18n import LANGUAGE_OPTIONS, resolve_supported_locale, translate, translate_message
from nmos_common.system_settings import DEFAULT_UI_LOCALE, load_system_settings, save_system_settings
from nmos_greeter import network_model, persistence_actions, ui_composition
from nmos_greeter.client import PersistenceClient
from nmos_greeter.state import load_state, save_state


class GreeterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Setup")
        self.set_default_size(860, 560)
        self.logger = logging.getLogger("nmos.greeter")

        persisted_settings = load_system_settings()
        self.state = {**persisted_settings, **load_state()}
        self.system_settings = dict(persisted_settings)
        self.save_state = save_state
        self.language_values = [locale for locale, _label in LANGUAGE_OPTIONS]
        self.network_policy_values = ["tor", "direct", "offline"]
        self.ui_locale = resolve_supported_locale(self.state.get("locale", os.environ.get("LANG", DEFAULT_UI_LOCALE)))
        self.page_order = self.resolve_page_order()
        self.network_status = self.default_network_status()
        self.persistence_state: dict = {}
        self.persistence_client_factory = PersistenceClient
        self.persistence_init_error = ""
        self.page_index = 0
        self.persistence_action_in_progress = False
        self.persistence_action_name = ""
        self.persistence_refresh_in_progress = False
        self.persistence_refresh_pending = False
        self.status_source = ""
        self.network_refresh_pending_id = 0
        self.network_refresh_force = False
        self.network_monitors: list[Gio.FileMonitor] = []
        self.page_widgets: dict[str, Gtk.Widget] = {}

        ui_composition.build_ui(self)
        self.apply_translations()
        self.restore_state()
        self.apply_settings_ui_policy()
        self.update_persistence_actions({})
        self.refresh_persistence()
        self.refresh_network(force_status=True)
        self.setup_network_watchers()
        self.update_navigation()
        GLib.timeout_add_seconds(10, self.poll_runtime)

    def tr(self, source_text: str, **kwargs) -> str:
        return translate(self.ui_locale, source_text, **kwargs)

    def translate_message(self, text: str) -> str:
        return translate_message(self.ui_locale, text)

    def resolve_page_order(self) -> list[str]:
        return ui_composition.resolve_page_order(self)

    def default_network_status(self) -> dict:
        return network_model.default_network_status(self)

    def current_page_key(self) -> str:
        return ui_composition.current_page_key(self)

    def current_language_code(self) -> str:
        return ui_composition.current_language_code(self)

    def current_language_name(self) -> str:
        return ui_composition.current_language_name(self)

    def current_network_policy(self) -> str:
        return ui_composition.current_network_policy(self)

    def current_network_policy_name(self) -> str:
        return ui_composition.current_network_policy_name(self)

    def action_label(self, action: str) -> str:
        return ui_composition.current_network_policy_name(self) if action == "policy" else self.tr(action.capitalize()).lower()

    def apply_translations(self) -> None:
        ui_composition.apply_translations(self)

    def apply_settings_ui_policy(self) -> None:
        ui_composition.apply_settings_ui_policy(self)

    def restore_state(self) -> None:
        ui_composition.restore_state(self)

    def current_string(self, dropdown: Gtk.DropDown) -> str:
        return ui_composition.current_string(dropdown)

    def set_status(self, text: str, *, source: str = "event", force: bool = True) -> None:
        ui_composition.set_status(self, text, source=source, force=force)

    def collect_state(self) -> dict:
        return ui_composition.collect_state(self)

    def refresh_network(self, *, force_status: bool = False) -> None:
        network_model.refresh_network(self, force_status=force_status)

    def refresh_persistence(self) -> None:
        persistence_actions.refresh_persistence(self)

    def run_persistence_refresh_worker(self) -> None:
        persistence_actions.run_persistence_refresh_worker(self)

    def complete_persistence_refresh(self, state: dict | None, error: str) -> bool:
        return persistence_actions.complete_persistence_refresh(self, state, error)

    def render_persistence_state(self, state: dict) -> str:
        return persistence_actions.render_persistence_state(self, state)

    def update_persistence_actions(self, state: dict) -> None:
        persistence_actions.update_persistence_actions(self, state)

    def persist_pending_state(self) -> bool:
        self.state = self.collect_state()
        try:
            self.save_state(self.state)
        except (OSError, ValueError, RuntimeError) as exc:
            self.logger.error("unable to save pending settings: %s", exc)
            self.set_status(self.tr("Unable to save pending settings: {error}", error=self.tr("internal error")))
            return False
        return True

    def apply_locale(self) -> bool:
        if not self.persist_pending_state():
            return False
        self.ui_locale = resolve_supported_locale(self.state.get("locale", DEFAULT_UI_LOCALE))
        self.apply_translations()
        self.set_status(self.tr("Language will be applied as {language}.", language=self.current_language_name()))
        return True

    def apply_keyboard(self) -> bool:
        if not self.persist_pending_state():
            return False
        self.set_status(self.tr("Keyboard layout will be applied as {layout}.", layout=self.current_string(self.keyboard_combo)))
        return True

    def apply_network_preferences(self) -> bool:
        if not self.persist_pending_state():
            return False
        self.apply_settings_ui_policy()
        self.set_status(
            self.tr("Network policy will be applied as {policy}.", policy=self.current_network_policy_name())
        )
        return True

    def on_refresh_network(self, _button: Gtk.Button) -> None:
        self.refresh_network(force_status=True)

    def on_network_policy_changed(self, *_args) -> None:
        self.apply_settings_ui_policy()
        self.update_navigation()

    def on_allow_brave_browser_toggled(self, *_args) -> None:
        self.update_navigation()

    def on_create_persistence(self, _button: Gtk.Button) -> None:
        persistence_actions.on_create_persistence(self, _button)

    def on_unlock_persistence(self, _button: Gtk.Button) -> None:
        persistence_actions.on_unlock_persistence(self, _button)

    def on_lock_persistence(self, _button: Gtk.Button) -> None:
        persistence_actions.on_lock_persistence(self, _button)

    def on_repair_persistence(self, _button: Gtk.Button) -> None:
        persistence_actions.on_repair_persistence(self, _button)

    def start_persistence_action(self, action: str, passphrase: str | None = None) -> None:
        persistence_actions.start_persistence_action(self, action, passphrase)

    def run_persistence_action_worker(self, action: str, passphrase: str | None) -> None:
        persistence_actions.run_persistence_action_worker(self, action, passphrase)

    def complete_persistence_action(self, action: str, response: dict | None, error: str) -> bool:
        return persistence_actions.complete_persistence_action(self, action, response, error)

    def handle_persistence_response(self, action: str, response: dict) -> None:
        persistence_actions.handle_persistence_response(self, action, response)

    def on_back(self, _button: Gtk.Button) -> None:
        if self.page_index > 0:
            self.page_index -= 1
        self.stack.set_visible_child_name(f"page-{self.page_index}")
        self.update_navigation()

    def on_next(self, _button: Gtk.Button) -> None:
        current_key = self.current_page_key()
        if current_key == "language" and not self.apply_locale():
            return
        if current_key == "keyboard" and not self.apply_keyboard():
            return
        if current_key == "network" and not self.apply_network_preferences():
            return
        if self.page_index < len(self.page_order) - 1:
            self.page_index += 1
        self.stack.set_visible_child_name(f"page-{self.page_index}")
        self.update_navigation()

    def close_after_apply(self) -> bool:
        self.close()
        return GLib.SOURCE_REMOVE

    def on_finish(self, _button: Gtk.Button) -> None:
        if not self.can_finish():
            self.set_status(self.tr("Encrypted vault activity is still running."))
            return
        state = self.collect_state()
        try:
            self.save_state(state)
            self.system_settings = save_system_settings(state)
            self.state = dict(self.system_settings)
        except (OSError, ValueError, RuntimeError) as exc:
            self.logger.error("failed to save system settings: %s", exc)
            self.set_status(self.tr("Failed to save system settings: {error}", error=self.tr("internal error")))
            return
        self.set_status(self.tr("Settings saved. Some privacy changes apply on the next boot."))
        GLib.timeout_add_seconds(2, self.close_after_apply)

    def update_navigation(self) -> None:
        ui_composition.update_navigation(self)

    def can_finish(self) -> bool:
        return ui_composition.can_finish(self)

    def poll_runtime(self) -> bool:
        if not self.persistence_action_in_progress:
            self.refresh_persistence()
        self.refresh_network()
        return True

    def setup_network_watchers(self) -> None:
        network_model.setup_network_watchers(self)

    def on_network_file_changed(self, _monitor, _file, _other_file, event_type) -> None:
        network_model.on_network_file_changed(self, _monitor, _file, _other_file, event_type)

    def queue_network_refresh(self, *, force_status: bool = False) -> None:
        network_model.queue_network_refresh(self, force_status=force_status)

    def run_queued_network_refresh(self) -> bool:
        return network_model.run_queued_network_refresh(self)


class GreeterApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.nmos.Greeter")

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = GreeterWindow(self)
        window.present()


def main() -> None:
    app = GreeterApplication()
    app.run([])


if __name__ == "__main__":
    main()
