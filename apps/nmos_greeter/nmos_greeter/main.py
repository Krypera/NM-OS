from __future__ import annotations

import threading

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk

from nmos_common.boot_mode import MODE_COMPAT, MODE_FLEXIBLE, MODE_OFFLINE, MODE_RECOVERY, MODE_STRICT
from nmos_greeter.client import PersistenceClient, read_boot_mode_profile, read_network_status
from nmos_greeter.gdmclient import GdmLoginClient
from nmos_greeter.state import load_state, save_state


class GreeterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Greeter")
        self.set_default_size(860, 560)

        self.state = load_state()
        self.boot_mode_profile = read_boot_mode_profile()
        self.boot_mode = str(self.boot_mode_profile.get("mode", MODE_STRICT))
        self.page_order = self.resolve_page_order()
        self.network_status = self.default_network_status()
        self.persistence_state: dict = {}
        self.persistence_client_factory = PersistenceClient
        self.persistence_init_error = ""
        self.gdm_init_error = ""
        try:
            self.gdm_client = GdmLoginClient(
                session_opened_cb=self.on_session_opened,
                problem_cb=self.on_session_problem,
            )
        except Exception as exc:
            self.gdm_client = None
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
        title = Gtk.Label(label="NM-OS")
        title.add_css_class("title-1")
        title.set_xalign(0)
        subtitle = Gtk.Label(label="Prepare your session before entering the desktop.")
        subtitle.set_xalign(0)
        self.mode_banner = Gtk.Label(xalign=0)
        self.mode_banner.add_css_class("caption")
        header.append(title)
        header.append(subtitle)
        header.append(self.mode_banner)
        root.append(header)

        self.session_status = Gtk.Label(xalign=0)
        self.session_status.add_css_class("caption")
        root.append(self.session_status)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)

        self.language_combo = self._combo(["en_US.UTF-8", "tr_TR.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"])
        self.keyboard_combo = self._combo(["us", "tr", "de", "fr"])
        self.network_progress = Gtk.ProgressBar()
        self.network_label = Gtk.Label(xalign=0)
        self.network_refresh = Gtk.Button(label="Refresh network status")
        self.network_refresh.connect("clicked", self.on_refresh_network)
        self.allow_offline = Gtk.CheckButton(label="Continue to desktop while network stays blocked")
        self.allow_offline.connect("toggled", self.on_allow_offline_toggled)

        self.persistence_label = Gtk.Label(xalign=0)
        self.persistence_password = Gtk.PasswordEntry()
        self.persistence_create = Gtk.Button(label="Create")
        self.persistence_unlock = Gtk.Button(label="Unlock")
        self.persistence_lock = Gtk.Button(label="Lock")
        self.persistence_repair = Gtk.Button(label="Repair")
        self.persistence_create.connect("clicked", self.on_create_persistence)
        self.persistence_unlock.connect("clicked", self.on_unlock_persistence)
        self.persistence_lock.connect("clicked", self.on_lock_persistence)
        self.persistence_repair.connect("clicked", self.on_repair_persistence)

        self.page_widgets = {
            "language": self._page("Language", "Choose the session language.", self.language_combo),
            "keyboard": self._page("Keyboard", "Choose the keyboard layout.", self.keyboard_combo),
            "network": self._network_page(),
            "persistence": self._persistence_page(),
        }

        for index, key in enumerate(self.page_order):
            self.stack.add_titled(self.page_widgets[key], f"page-{index}", f"Page {index + 1}")

        root.append(self.stack)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.back_button = Gtk.Button(label="Back")
        self.next_button = Gtk.Button(label="Next")
        self.finish_button = Gtk.Button(label="Finish")
        self.back_button.connect("clicked", self.on_back)
        self.next_button.connect("clicked", self.on_next)
        self.finish_button.connect("clicked", self.on_finish)
        nav.append(self.back_button)
        nav.append(self.next_button)
        nav.append(self.finish_button)
        root.append(nav)

        self.set_content(root)
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

    def _page(self, title_text: str, subtitle_text: str, control: Gtk.Widget) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        title = Gtk.Label(label=title_text, xalign=0)
        title.add_css_class("title-3")
        subtitle = Gtk.Label(label=subtitle_text, xalign=0)
        box.append(title)
        box.append(subtitle)
        box.append(control)
        return box

    def _network_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        title = Gtk.Label(label="Network", xalign=0)
        title.add_css_class("title-3")
        box.append(title)
        box.append(self.network_label)
        box.append(self.network_progress)
        box.append(self.network_refresh)
        box.append(self.allow_offline)
        return box

    def _persistence_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        title = Gtk.Label(label="Persistence", xalign=0)
        title.add_css_class("title-3")
        box.append(title)
        box.append(self.persistence_label)
        box.append(self.persistence_password)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.append(self.persistence_create)
        actions.append(self.persistence_unlock)
        actions.append(self.persistence_lock)
        actions.append(self.persistence_repair)
        box.append(actions)
        return box

    def mode_title(self) -> str:
        return {
            MODE_STRICT: "Strict",
            MODE_FLEXIBLE: "Flexible",
            MODE_OFFLINE: "Offline",
            MODE_RECOVERY: "Recovery",
            MODE_COMPAT: "Hardware Compatibility",
        }.get(self.boot_mode, "Strict")

    def mode_description(self) -> str:
        if self.boot_mode == MODE_FLEXIBLE:
            return "Tor-first with a more relaxed onboarding flow."
        if self.boot_mode == MODE_OFFLINE:
            return "Networking is intentionally disabled for this session."
        if self.boot_mode == MODE_RECOVERY:
            return "Recovery-first session with networking intentionally disabled."
        if self.boot_mode == MODE_COMPAT:
            return "Compatibility boot options are enabled while keeping strict network policy."
        return "Tor-first strict profile is active."

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
        self.mode_banner.set_text(f"Mode: {self.mode_title()} - {self.mode_description()}")
        if self.is_network_disabled_mode():
            self.allow_offline.set_active(True)
            self.allow_offline.set_sensitive(False)
            self.network_refresh.set_sensitive(False)
        elif self.boot_mode == MODE_FLEXIBLE:
            self.allow_offline.set_active(True)

    def restore_state(self) -> None:
        locale = self.state.get("locale", "en_US.UTF-8")
        keyboard = self.state.get("keyboard", "us")
        self._select_string(self.language_combo, locale)
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
            "locale": self.current_string(self.language_combo),
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
        self.network_label.set_text(f"{status['summary']} ({status['progress']}%)")
        self.network_progress.set_fraction(status["progress"] / 100.0)
        if self.is_network_disabled_mode():
            self.set_status("Network is intentionally disabled for this boot mode.", source="network", force=force_status)
        elif status.get("last_error"):
            self.set_status(f"Network status: {status['last_error']}", source="network", force=force_status)
        elif status["ready"]:
            self.set_status("Tor connection is ready.", source="network", force=force_status)
        else:
            self.set_status("Waiting for Tor to become ready.", source="network", force=force_status)
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
            self.persistence_label.set_text(f"Persistence backend unavailable: {error}")
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
        if last_error:
            return f"Persistence error: {last_error}"
        if busy:
            return "Persistence operation is in progress."
        if created and unlocked:
            return "Persistence is unlocked and ready."
        if created:
            return f"Persistence exists on {device or 'the boot USB'} and can be unlocked."
        if reason == "no_free_space":
            return f"Persistence cannot be created on {device or 'the boot USB'} because less than 1 GiB of free space remains."
        if reason == "unsupported_boot_device":
            return "Persistence creation is disabled because NM-OS was not started from a writable USB device."
        if reason == "unsupported_layout":
            return "Persistence creation is disabled because the boot USB layout cannot safely accept an appended partition."
        if reason == "read_only":
            return "Persistence creation is disabled because the boot USB is read-only."
        if can_create:
            return f"Persistence can be created on {device or 'the boot USB'}."
        if reason == "already_exists":
            return f"Persistence already exists on {device or 'the boot USB'}."
        return "Persistence state is unavailable."

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
        locale = self.current_string(self.language_combo)
        self.state["locale"] = locale
        try:
            save_state(self.state)
        except OSError as exc:
            self.set_status(f"Unable to save language selection: {exc}")
            return False
        self.set_status(f"Language will be applied as {locale}.")
        return True

    def apply_keyboard(self) -> bool:
        layout = self.current_string(self.keyboard_combo)
        self.state["keyboard"] = layout
        try:
            save_state(self.state)
        except OSError as exc:
            self.set_status(f"Unable to save keyboard selection: {exc}")
            return False
        self.set_status(f"Keyboard layout will be applied as {layout}.")
        return True

    def on_refresh_network(self, _button: Gtk.Button) -> None:
        self.refresh_network(force_status=True)

    def on_allow_offline_toggled(self, _button: Gtk.CheckButton) -> None:
        if self.is_network_disabled_mode():
            self.set_status("This boot mode is intentionally offline.")
        elif self.allow_offline.get_active():
            self.set_status("You can continue to desktop now, but network traffic stays blocked until Tor is ready.")
        else:
            self.set_status("Continue without network is disabled. Wait for Tor readiness to proceed.")
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
            self.set_status(f"Persistence {self.persistence_action_name} is still running. Please wait.")
            return
        if self.persistence_refresh_in_progress:
            self.set_status("Persistence status is refreshing. Please wait.")
            self.persistence_refresh_pending = True
            return

        self.persistence_action_in_progress = True
        self.persistence_action_name = action
        busy_state = dict(self.persistence_state)
        busy_state["busy"] = True
        self.persistence_state = busy_state
        self.persistence_label.set_text(f"Persistence {action} is in progress...")
        self.update_persistence_actions(busy_state)
        self.update_navigation()
        self.set_status(f"Starting persistence {action}...")
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
            self.set_status(f"Persistence {action} failed: {error}")
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
            self.set_status(f"Persistence {action} failed: {response['last_error']}")
            return
        self.set_status(f"Persistence {action} request completed.")

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
            self.set_status("Session is not ready yet.")
            return
        try:
            save_state(self.collect_state())
        except Exception as exc:
            self.set_status(f"Failed to save greeter state: {exc}")
            return
        if self.gdm_client is None:
            if self.gdm_init_error:
                self.set_status(f"GDM session control is unavailable: {self.gdm_init_error}")
            else:
                self.set_status("Greeter state saved, but GDM session control is unavailable.")
            return
        self.session_start_in_progress = True
        self.set_sensitive(False)
        self.set_status("Starting the live session...")
        self.arm_session_start_timeout()
        try:
            self.gdm_client.start_session()
        except Exception as exc:
            self.session_start_in_progress = False
            self.clear_session_start_timeout()
            self.set_sensitive(True)
            self.set_status(f"Failed to start the live session: {exc}")

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
            self.set_status(f"Live session start timed out. Login flow reset failed: {cancel_error}")
        else:
            self.set_status("Live session start timed out. Login flow was reset.")
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
        self.set_status(f"Live session start failed: {problem}")


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
