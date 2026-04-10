from __future__ import annotations

import os
import threading

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk

from nmos_common.boot_mode import MODE_COMPAT, MODE_FLEXIBLE, MODE_OFFLINE, MODE_RECOVERY, MODE_STRICT
from nmos_common.i18n import (
    DEFAULT_UI_LOCALE,
    LANGUAGE_OPTIONS,
    display_language_name,
    resolve_supported_locale,
    translate,
    translate_message,
)
from nmos_greeter.client import PersistenceClient, read_boot_mode_profile, read_network_status
from nmos_greeter.gdmclient import GdmLoginClient
from nmos_greeter.state import load_state, save_state


class GreeterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Greeter")
        self.set_default_size(860, 560)

        self.state = load_state()
        self.language_values = [locale for locale, _label in LANGUAGE_OPTIONS]
        self.ui_locale = resolve_supported_locale(self.state.get("locale", os.environ.get("LANG", DEFAULT_UI_LOCALE)))
        self.boot_mode_profile = read_boot_mode_profile()
        self.boot_mode = str(self.boot_mode_profile.get("mode", MODE_STRICT))
        self.page_order = self.resolve_page_order()
        self.network_status = self.default_network_status()
        self.persistence_state: dict = {}
        self.persistence_client_factory = PersistenceClient
        self.persistence_init_error = ""
        self.gdm_init_error = ""
        self.gdm_client: GdmLoginClient | None = None
        try:
            self.gdm_client = GdmLoginClient(
                session_opened_cb=self.on_session_opened,
                problem_cb=self.on_session_problem,
            )
        except Exception as exc:
            self.gdm_init_error = str(exc)
        self.page_index = 0
        self.session_start_timeout_id = 0
        self.session_start_in_progress = False
        self.persistence_action_in_progress = False
        self.persistence_action_name = ""
        self.persistence_refresh_in_progress = False
        self.persistence_refresh_pending = False
        self.status_source = ""
        self.network_refresh_pending_id = 0
        self.network_refresh_force = False
        self.network_monitors: list[Gio.FileMonitor] = []
        self.page_widgets: dict[str, Gtk.Widget] = {}

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        root.set_margin_top(24)
        root.set_margin_bottom(24)
        root.set_margin_start(24)
        root.set_margin_end(24)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.header_title_label = Gtk.Label(label="NM-OS")
        self.header_title_label.add_css_class("title-1")
        self.header_title_label.set_xalign(0)
        self.header_subtitle_label = Gtk.Label(xalign=0)
        self.mode_banner = Gtk.Label(xalign=0)
        self.mode_banner.add_css_class("caption")
        header.append(self.header_title_label)
        header.append(self.header_subtitle_label)
        header.append(self.mode_banner)
        root.append(header)

        self.session_status = Gtk.Label(xalign=0)
        self.session_status.add_css_class("caption")
        root.append(self.session_status)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)

        self.language_combo = self._combo([display_language_name(locale) for locale in self.language_values])
        self.keyboard_combo = self._combo(["us", "tr", "de", "fr"])
        self.network_progress = Gtk.ProgressBar()
        self.network_label = Gtk.Label(xalign=0)
        self.network_refresh = Gtk.Button()
        self.network_refresh.connect("clicked", self.on_refresh_network)
        self.allow_offline = Gtk.CheckButton()
        self.allow_offline.connect("toggled", self.on_allow_offline_toggled)

        self.persistence_label = Gtk.Label(xalign=0)
        self.persistence_password = Gtk.PasswordEntry()
        self.persistence_create = Gtk.Button()
        self.persistence_unlock = Gtk.Button()
        self.persistence_lock = Gtk.Button()
        self.persistence_repair = Gtk.Button()
        self.persistence_create.connect("clicked", self.on_create_persistence)
        self.persistence_unlock.connect("clicked", self.on_unlock_persistence)
        self.persistence_lock.connect("clicked", self.on_lock_persistence)
        self.persistence_repair.connect("clicked", self.on_repair_persistence)

        self.page_widgets = {
            "language": self._page("language", "Language", "Choose the session language.", self.language_combo),
            "keyboard": self._page("keyboard", "Keyboard", "Choose the keyboard layout.", self.keyboard_combo),
            "network": self._network_page(),
            "persistence": self._persistence_page(),
        }

        for index, key in enumerate(self.page_order):
            self.stack.add_titled(self.page_widgets[key], f"page-{index}", f"Page {index + 1}")

        root.append(self.stack)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.back_button = Gtk.Button()
        self.next_button = Gtk.Button()
        self.finish_button = Gtk.Button()
        self.back_button.connect("clicked", self.on_back)
        self.next_button.connect("clicked", self.on_next)
        self.finish_button.connect("clicked", self.on_finish)
        nav.append(self.back_button)
        nav.append(self.next_button)
        nav.append(self.finish_button)
        root.append(nav)

        self.set_content(root)
        self.apply_translations()
        self.apply_mode_ui_policy()
        self.restore_state()
        self.update_persistence_actions({})
        self.refresh_persistence()
        self.refresh_network(force_status=True)
        self.setup_network_watchers()
        self.update_navigation()
        GLib.timeout_add_seconds(10, self.poll_runtime)

    def _combo(self, values: list[str]) -> Gtk.DropDown:
        model = Gtk.StringList.new(values)
        return Gtk.DropDown(model=model)

    def _page(self, page_key: str, title_text: str, subtitle_text: str, control: Gtk.Widget) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        title = Gtk.Label(label=title_text, xalign=0)
        title.add_css_class("title-3")
        subtitle = Gtk.Label(label=subtitle_text, xalign=0)
        setattr(self, f"{page_key}_title_label", title)
        setattr(self, f"{page_key}_subtitle_label", subtitle)
        box.append(title)
        box.append(subtitle)
        box.append(control)
        return box

    def _network_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.network_title_label = Gtk.Label(label="Network", xalign=0)
        self.network_title_label.add_css_class("title-3")
        box.append(self.network_title_label)
        box.append(self.network_label)
        box.append(self.network_progress)
        box.append(self.network_refresh)
        box.append(self.allow_offline)
        return box

    def _persistence_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.persistence_title_label = Gtk.Label(label="Persistence", xalign=0)
        self.persistence_title_label.add_css_class("title-3")
        box.append(self.persistence_title_label)
        box.append(self.persistence_label)
        box.append(self.persistence_password)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.append(self.persistence_create)
        actions.append(self.persistence_unlock)
        actions.append(self.persistence_lock)
        actions.append(self.persistence_repair)
        box.append(actions)
        return box

    def tr(self, source_text: str, **kwargs) -> str:
        return translate(self.ui_locale, source_text, **kwargs)

    def translate_message(self, text: str) -> str:
        return translate_message(self.ui_locale, text)

    def current_language_code(self) -> str:
        selected = self.language_combo.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION or selected >= len(self.language_values):
            self.language_combo.set_selected(0)
            return self.language_values[0]
        return self.language_values[selected]

    def current_language_name(self) -> str:
        return display_language_name(self.current_language_code())

    def action_label(self, action: str) -> str:
        return self.tr(action.capitalize()).lower()

    def apply_translations(self) -> None:
        self.set_title(self.tr("NM-OS Greeter"))
        self.header_subtitle_label.set_text(self.tr("Prepare your session before entering the desktop."))
        self.language_title_label.set_text(self.tr("Language"))
        self.language_subtitle_label.set_text(self.tr("Choose the session language."))
        self.keyboard_title_label.set_text(self.tr("Keyboard"))
        self.keyboard_subtitle_label.set_text(self.tr("Choose the keyboard layout."))
        self.network_title_label.set_text(self.tr("Network"))
        self.persistence_title_label.set_text(self.tr("Persistence"))
        self.network_refresh.set_label(self.tr("Refresh network status"))
        self.allow_offline.set_label(self.tr("Continue to desktop while network stays blocked"))
        self.persistence_create.set_label(self.tr("Create"))
        self.persistence_unlock.set_label(self.tr("Unlock"))
        self.persistence_lock.set_label(self.tr("Lock"))
        self.persistence_repair.set_label(self.tr("Repair"))
        self.back_button.set_label(self.tr("Back"))
        self.next_button.set_label(self.tr("Next"))
        self.finish_button.set_label(self.tr("Finish"))
        self.mode_banner.set_text(self.tr("Mode: {mode} - {description}", mode=self.mode_title(), description=self.mode_description()))
        if self.persistence_init_error:
            self.persistence_label.set_text(
                self.tr(
                    "Persistence backend unavailable: {error}",
                    error=self.translate_message(self.persistence_init_error),
                )
            )
        elif self.persistence_state:
            self.persistence_label.set_text(self.render_persistence_state(self.persistence_state))

    def mode_title(self) -> str:
        return {
            MODE_STRICT: self.tr("Strict"),
            MODE_FLEXIBLE: self.tr("Flexible"),
            MODE_OFFLINE: self.tr("Offline"),
            MODE_RECOVERY: self.tr("Recovery"),
            MODE_COMPAT: self.tr("Hardware Compatibility"),
        }.get(self.boot_mode, self.tr("Strict"))

    def mode_description(self) -> str:
        if self.boot_mode == MODE_FLEXIBLE:
            return self.tr("Tor-first with a more relaxed onboarding flow.")
        if self.boot_mode == MODE_OFFLINE:
            return self.tr("Networking is intentionally disabled for this session.")
        if self.boot_mode == MODE_RECOVERY:
            return self.tr("Recovery-first session with networking intentionally disabled.")
        if self.boot_mode == MODE_COMPAT:
            return self.tr("Compatibility boot options are enabled while keeping strict network policy.")
        return self.tr("Tor-first strict profile is active.")

    def is_network_disabled_mode(self) -> bool:
        return self.boot_mode in {MODE_OFFLINE, MODE_RECOVERY}

    def current_page_key(self) -> str:
        return self.page_order[self.page_index]

    def resolve_page_order(self) -> list[str]:
        if self.boot_mode == MODE_RECOVERY:
            return ["persistence", "language", "keyboard", "network"]
        return ["language", "keyboard", "network", "persistence"]

    def default_network_status(self) -> dict:
        if self.boot_mode in {MODE_OFFLINE, MODE_RECOVERY}:
            return {
                "ready": False,
                "progress": 0,
                "phase": "disabled",
                "summary": f"Network is disabled by boot mode ({self.boot_mode}).",
                "last_error": "",
                "updated_at": "",
            }
        return {
            "ready": False,
            "progress": 0,
            "phase": "bootstrap",
            "summary": "Waiting for Tor",
            "last_error": "",
            "updated_at": "",
        }

    def apply_mode_ui_policy(self) -> None:
        self.mode_banner.set_text(self.tr("Mode: {mode} - {description}", mode=self.mode_title(), description=self.mode_description()))
        if self.is_network_disabled_mode():
            self.allow_offline.set_active(True)
            self.allow_offline.set_sensitive(False)
            self.network_refresh.set_sensitive(False)
        elif self.boot_mode == MODE_FLEXIBLE:
            self.allow_offline.set_active(True)

    def restore_state(self) -> None:
        locale = self.state.get("locale", "en_US.UTF-8")
        keyboard = self.state.get("keyboard", "us")
        self._select_language(locale)
        self._select_string(self.keyboard_combo, keyboard)
        if self.is_network_disabled_mode():
            self.allow_offline.set_active(True)
        elif self.boot_mode == MODE_FLEXIBLE and "allow_offline" not in self.state:
            self.allow_offline.set_active(True)
        else:
            self.allow_offline.set_active(bool(self.state.get("allow_offline", False)))

    def _select_string(self, dropdown: Gtk.DropDown, value: str) -> None:
        model = dropdown.get_model()
        for index in range(model.get_n_items()):
            if model.get_string(index) == value:
                dropdown.set_selected(index)
                return

    def _select_language(self, locale: str) -> None:
        resolved = resolve_supported_locale(locale)
        for index, value in enumerate(self.language_values):
            if value == resolved:
                self.language_combo.set_selected(index)
                return
        self.language_combo.set_selected(0)

    def current_string(self, dropdown: Gtk.DropDown) -> str:
        model = dropdown.get_model()
        selected = dropdown.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION or selected >= model.get_n_items():
            if model.get_n_items() == 0:
                return ""
            dropdown.set_selected(0)
            selected = 0
        return model.get_string(selected)

    def set_status(self, text: str, *, source: str = "event", force: bool = True) -> None:
        if not force and source == "network" and self.status_source not in {"", "network"}:
            return
        self.status_source = source
        self.session_status.set_text(text)

    def collect_state(self) -> dict:
        return {
            "locale": self.current_language_code(),
            "keyboard": self.current_string(self.keyboard_combo),
            "allow_offline": self.allow_offline.get_active(),
        }

    def can_bypass_network(self) -> bool:
        if self.is_network_disabled_mode():
            return True
        if self.boot_mode == MODE_FLEXIBLE:
            return True
        return self.allow_offline.get_active()

    def can_advance_from_network(self) -> bool:
        if self.is_network_disabled_mode():
            return True
        return bool(self.network_status.get("ready")) or self.can_bypass_network()

    def can_finish(self) -> bool:
        if self.persistence_state.get("busy") or self.persistence_action_in_progress or self.persistence_refresh_in_progress:
            return False
        return self.can_advance_from_network()

    def refresh_network(self, *, force_status: bool = False) -> None:
        if self.is_network_disabled_mode():
            status = self.default_network_status()
        else:
            try:
                status = read_network_status()
            except Exception as exc:
                status = {
                    "ready": False,
                    "progress": 0,
                    "phase": "failed",
                    "summary": "Unable to read network status",
                    "last_error": str(exc),
                    "updated_at": "",
                }
        self.network_status = status
        summary = self.translate_message(str(status["summary"]))
        self.network_label.set_text(f"{summary} ({status['progress']}%)")
        self.network_progress.set_fraction(status["progress"] / 100.0)
        if self.is_network_disabled_mode():
            self.set_status(self.tr("Network is intentionally disabled for this boot mode."), source="network", force=force_status)
        elif status.get("last_error"):
            self.set_status(
                self.tr("Network status: {error}", error=self.translate_message(str(status["last_error"]))),
                source="network",
                force=force_status,
            )
        elif status["ready"]:
            self.set_status(self.tr("Tor connection is ready."), source="network", force=force_status)
        else:
            self.set_status(self.tr("Waiting for Tor to become ready."), source="network", force=force_status)
        self.update_navigation()

    def refresh_persistence(self) -> None:
        if self.persistence_action_in_progress:
            return
        if self.persistence_refresh_in_progress:
            self.persistence_refresh_pending = True
            return
        self.persistence_refresh_in_progress = True
        self.update_persistence_actions(self.persistence_state)
        self.update_navigation()
        thread = threading.Thread(target=self.run_persistence_refresh_worker, daemon=True)
        thread.start()

    def run_persistence_refresh_worker(self) -> None:
        try:
            client = self.persistence_client_factory()
            state = client.get_state()
            GLib.idle_add(self.complete_persistence_refresh, dict(state), "")
        except Exception as exc:
            GLib.idle_add(self.complete_persistence_refresh, None, str(exc))

    def complete_persistence_refresh(self, state: dict | None, error: str) -> bool:
        self.persistence_refresh_in_progress = False
        if error:
            self.persistence_state = {}
            self.persistence_init_error = error
            self.persistence_label.set_text(
                self.tr("Persistence backend unavailable: {error}", error=self.translate_message(error))
            )
            self.update_persistence_actions({})
            self.update_navigation()
        elif state is not None:
            self.persistence_state = dict(state)
            self.persistence_init_error = ""
            self.persistence_label.set_text(self.render_persistence_state(state))
            self.update_persistence_actions(state)
            self.update_navigation()

        if self.persistence_refresh_pending and not self.persistence_action_in_progress:
            self.persistence_refresh_pending = False
            self.refresh_persistence()
        return GLib.SOURCE_REMOVE

    def render_persistence_state(self, state: dict) -> str:
        created = state.get("created", False)
        unlocked = state.get("unlocked", False)
        busy = state.get("busy", False)
        can_create = state.get("can_create", False)
        reason = state.get("reason", "")
        device = state.get("device", "")
        last_error = state.get("last_error", "")
        device_label = device or self.tr("the boot USB")
        if last_error:
            return self.tr("Persistence error: {error}", error=self.translate_message(str(last_error)))
        if busy:
            return self.tr("Persistence operation is in progress.")
        if created and unlocked:
            return self.tr("Persistence is unlocked and ready.")
        if created:
            return self.tr("Persistence exists on {device} and can be unlocked.", device=device_label)
        if reason == "no_free_space":
            return self.tr(
                "Persistence cannot be created on {device} because less than 1 GiB of free space remains.",
                device=device_label,
            )
        if reason == "unsupported_boot_device":
            return self.tr("Persistence creation is disabled because NM-OS was not started from a writable USB device.")
        if reason == "unsupported_layout":
            return self.tr(
                "Persistence creation is disabled because the boot USB layout cannot safely accept an appended partition."
            )
        if reason == "read_only":
            return self.tr("Persistence creation is disabled because the boot USB is read-only.")
        if can_create:
            return self.tr("Persistence can be created on {device}.", device=device_label)
        if reason == "already_exists":
            return self.tr("Persistence already exists on {device}.", device=device_label)
        return self.tr("Persistence state is unavailable.")

    def update_persistence_actions(self, state: dict) -> None:
        created = bool(state.get("created"))
        unlocked = bool(state.get("unlocked"))
        busy = bool(state.get("busy")) or self.persistence_action_in_progress or self.persistence_refresh_in_progress
        can_create = bool(state.get("can_create"))
        self.persistence_create.set_sensitive(can_create and not busy)
        self.persistence_unlock.set_sensitive(created and not unlocked and not busy)
        self.persistence_lock.set_sensitive(unlocked and not busy)
        self.persistence_repair.set_sensitive(created and unlocked and not busy)

    def apply_locale(self) -> bool:
        locale = self.current_language_code()
        self.state["locale"] = locale
        try:
            save_state(self.state)
        except OSError as exc:
            self.set_status(self.tr("Unable to save language selection: {error}", error=self.translate_message(str(exc))))
            return False
        self.ui_locale = resolve_supported_locale(locale)
        self.apply_translations()
        self.refresh_network(force_status=True)
        self.set_status(self.tr("Language will be applied as {language}.", language=self.current_language_name()))
        return True

    def apply_keyboard(self) -> bool:
        layout = self.current_string(self.keyboard_combo)
        self.state["keyboard"] = layout
        try:
            save_state(self.state)
        except OSError as exc:
            self.set_status(self.tr("Unable to save keyboard selection: {error}", error=self.translate_message(str(exc))))
            return False
        self.set_status(self.tr("Keyboard layout will be applied as {layout}.", layout=layout))
        return True

    def on_refresh_network(self, _button: Gtk.Button) -> None:
        self.refresh_network(force_status=True)

    def on_allow_offline_toggled(self, _button: Gtk.CheckButton) -> None:
        if self.is_network_disabled_mode():
            self.set_status(self.tr("This boot mode is intentionally offline."))
        elif self.allow_offline.get_active():
            self.set_status(self.tr("You can continue to desktop now, but network traffic stays blocked until Tor is ready."))
        else:
            self.set_status(self.tr("Continue without network is disabled. Wait for Tor readiness to proceed."))
        self.update_navigation()

    def on_create_persistence(self, _button: Gtk.Button) -> None:
        passphrase = self.persistence_password.get_text()
        self.persistence_password.set_text("")
        self.start_persistence_action("create", passphrase)

    def on_unlock_persistence(self, _button: Gtk.Button) -> None:
        passphrase = self.persistence_password.get_text()
        self.persistence_password.set_text("")
        self.start_persistence_action("unlock", passphrase)

    def on_lock_persistence(self, _button: Gtk.Button) -> None:
        self.start_persistence_action("lock")

    def on_repair_persistence(self, _button: Gtk.Button) -> None:
        self.start_persistence_action("repair")

    def start_persistence_action(self, action: str, passphrase: str | None = None) -> None:
        if self.persistence_action_in_progress:
            self.set_status(
                self.tr(
                    "Persistence {action} is still running. Please wait.",
                    action=self.action_label(self.persistence_action_name),
                )
            )
            return
        if self.persistence_refresh_in_progress:
            self.set_status(self.tr("Persistence status is refreshing. Please wait."))
            self.persistence_refresh_pending = True
            return

        self.persistence_action_in_progress = True
        self.persistence_action_name = action
        busy_state = dict(self.persistence_state)
        busy_state["busy"] = True
        self.persistence_state = busy_state
        self.persistence_label.set_text(self.tr("Persistence {action} is in progress...", action=self.action_label(action)))
        self.update_persistence_actions(busy_state)
        self.update_navigation()
        self.set_status(self.tr("Starting persistence {action}...", action=self.action_label(action)))
        thread = threading.Thread(
            target=self.run_persistence_action_worker,
            args=(action, passphrase),
            daemon=True,
        )
        thread.start()

    def run_persistence_action_worker(self, action: str, passphrase: str | None) -> None:
        try:
            client = self.persistence_client_factory()
            if action == "create":
                response = client.create(passphrase or "")
            elif action == "unlock":
                response = client.unlock(passphrase or "")
            elif action == "lock":
                response = client.lock()
            elif action == "repair":
                response = client.repair()
            else:
                raise RuntimeError(f"unsupported persistence action: {action}")
            GLib.idle_add(self.complete_persistence_action, action, dict(response), "")
        except Exception as exc:
            GLib.idle_add(self.complete_persistence_action, action, None, str(exc))

    def complete_persistence_action(self, action: str, response: dict | None, error: str) -> bool:
        self.persistence_action_in_progress = False
        self.persistence_action_name = ""
        if error:
            self.set_status(
                self.tr(
                    "Persistence {action} failed: {error}",
                    action=self.action_label(action),
                    error=self.translate_message(error),
                )
            )
            self.refresh_persistence()
            return GLib.SOURCE_REMOVE
        if response is not None:
            self.handle_persistence_response(action, response)
        else:
            self.refresh_persistence()
        return GLib.SOURCE_REMOVE

    def handle_persistence_response(self, action: str, response: dict) -> None:
        self.persistence_state = dict(response)
        self.persistence_label.set_text(self.render_persistence_state(response))
        self.update_persistence_actions(response)
        self.update_navigation()
        if response.get("last_error"):
            self.set_status(
                self.tr(
                    "Persistence {action} failed: {error}",
                    action=self.action_label(action),
                    error=self.translate_message(str(response["last_error"])),
                )
            )
            return
        self.set_status(self.tr("Persistence {action} request completed.", action=self.action_label(action)))

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
        if self.page_index < len(self.page_order) - 1:
            self.page_index += 1
        self.stack.set_visible_child_name(f"page-{self.page_index}")
        self.update_navigation()

    def on_finish(self, _button: Gtk.Button) -> None:
        if not self.can_finish():
            self.set_status(self.tr("Session is not ready yet."))
            return
        try:
            save_state(self.collect_state())
        except Exception as exc:
            self.set_status(self.tr("Failed to save greeter state: {error}", error=self.translate_message(str(exc))))
            return
        if self.gdm_client is None:
            if self.gdm_init_error:
                self.set_status(
                    self.tr(
                        "GDM session control is unavailable: {error}",
                        error=self.translate_message(self.gdm_init_error),
                    )
                )
            else:
                self.set_status(self.tr("Greeter state saved, but GDM session control is unavailable."))
            return
        self.session_start_in_progress = True
        self.set_sensitive(False)
        self.set_status(self.tr("Starting the live session..."))
        self.arm_session_start_timeout()
        try:
            self.gdm_client.start_session()
        except Exception as exc:
            self.session_start_in_progress = False
            self.clear_session_start_timeout()
            self.set_sensitive(True)
            self.set_status(self.tr("Failed to start the live session: {error}", error=self.translate_message(str(exc))))

    def update_navigation(self) -> None:
        self.back_button.set_sensitive(self.page_index > 0)
        self.next_button.set_visible(self.page_index < len(self.page_order) - 1)
        if self.current_page_key() == "network":
            self.next_button.set_sensitive(self.can_advance_from_network())
        else:
            self.next_button.set_sensitive(True)
        self.finish_button.set_visible(self.page_index == len(self.page_order) - 1)
        self.finish_button.set_sensitive(self.can_finish())

    def poll_runtime(self) -> bool:
        if self.session_start_in_progress:
            return True
        if not self.is_network_disabled_mode():
            self.refresh_network()
        if not self.persistence_action_in_progress:
            self.refresh_persistence()
        return True

    def setup_network_watchers(self) -> None:
        if self.is_network_disabled_mode():
            return
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
            monitor.connect("changed", self.on_network_file_changed)
            self.network_monitors.append(monitor)

    def on_network_file_changed(self, _monitor, _file, _other_file, event_type) -> None:
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
        self.queue_network_refresh()

    def queue_network_refresh(self, *, force_status: bool = False) -> None:
        self.network_refresh_force = self.network_refresh_force or force_status
        if self.network_refresh_pending_id:
            return
        self.network_refresh_pending_id = GLib.timeout_add(200, self.run_queued_network_refresh)

    def run_queued_network_refresh(self) -> bool:
        self.network_refresh_pending_id = 0
        force_status = self.network_refresh_force
        self.network_refresh_force = False
        self.refresh_network(force_status=force_status)
        return GLib.SOURCE_REMOVE

    def arm_session_start_timeout(self) -> None:
        self.clear_session_start_timeout()
        self.session_start_timeout_id = GLib.timeout_add_seconds(15, self.on_session_start_timeout)

    def clear_session_start_timeout(self) -> None:
        if self.session_start_timeout_id:
            GLib.source_remove(self.session_start_timeout_id)
            self.session_start_timeout_id = 0

    def on_session_start_timeout(self) -> bool:
        self.session_start_timeout_id = 0
        self.session_start_in_progress = False
        cancel_error = ""
        if self.gdm_client is not None:
            try:
                self.gdm_client.cancel_pending_login()
            except Exception as exc:
                cancel_error = str(exc)
        self.set_sensitive(True)
        if cancel_error:
            self.set_status(
                self.tr(
                    "Live session start timed out. Login flow reset failed: {error}",
                    error=self.translate_message(cancel_error),
                )
            )
        else:
            self.set_status(self.tr("Live session start timed out. Login flow was reset."))
        return GLib.SOURCE_REMOVE

    def on_session_opened(self) -> None:
        self.session_start_in_progress = False
        self.clear_session_start_timeout()
        self.close()

    def on_session_problem(self, problem: str) -> None:
        self.session_start_in_progress = False
        self.clear_session_start_timeout()
        if self.gdm_client is not None:
            try:
                self.gdm_client.cancel_pending_login()
            except Exception:
                pass
        self.set_sensitive(True)
        self.set_status(self.tr("Live session start failed: {problem}", problem=self.translate_message(problem)))


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
