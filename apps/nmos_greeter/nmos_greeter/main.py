from __future__ import annotations

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk

from nmos_greeter.client import PersistenceClient, read_network_status
from nmos_greeter.gdmclient import GdmLoginClient
from nmos_greeter.state import load_state, save_state


class GreeterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Greeter")
        self.set_default_size(860, 560)

        self.state = load_state()
        self.network_status = {"ready": False, "progress": 0, "summary": "Waiting for Tor", "last_error": ""}
        try:
            self.persistence = PersistenceClient()
        except Exception:
            self.persistence = None
        try:
            self.gdm_client = GdmLoginClient(
                session_opened_cb=self.on_session_opened,
                problem_cb=self.on_session_problem,
            )
        except Exception:
            self.gdm_client = None
        self.page_index = 0
        self.session_start_timeout_id = 0
        self.pages: list[Gtk.Widget] = []

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
        header.append(title)
        header.append(subtitle)
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
        self.allow_offline = Gtk.CheckButton(label="Continue without network")
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

        self.pages.append(self._page("Language", "Choose the session language.", self.language_combo))
        self.pages.append(self._page("Keyboard", "Choose the keyboard layout.", self.keyboard_combo))
        self.pages.append(self._network_page())
        self.pages.append(self._persistence_page())

        for index, page in enumerate(self.pages):
            self.stack.add_titled(page, f"page-{index}", f"Page {index + 1}")

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
        self.restore_state()
        self.refresh_persistence()
        self.refresh_network()
        self.update_navigation()
        GLib.timeout_add_seconds(3, self.poll_runtime)

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

    def restore_state(self) -> None:
        locale = self.state.get("locale", "en_US.UTF-8")
        keyboard = self.state.get("keyboard", "us")
        self._select_string(self.language_combo, locale)
        self._select_string(self.keyboard_combo, keyboard)
        self.allow_offline.set_active(bool(self.state.get("allow_offline", False)))

    def _select_string(self, dropdown: Gtk.DropDown, value: str) -> None:
        model = dropdown.get_model()
        for index in range(model.get_n_items()):
            if model.get_string(index) == value:
                dropdown.set_selected(index)
                return

    def current_string(self, dropdown: Gtk.DropDown) -> str:
        model = dropdown.get_model()
        return model.get_string(dropdown.get_selected())

    def set_status(self, text: str) -> None:
        self.session_status.set_text(text)

    def collect_state(self) -> dict:
        return {
            "locale": self.current_string(self.language_combo),
            "keyboard": self.current_string(self.keyboard_combo),
            "allow_offline": self.allow_offline.get_active(),
        }

    def can_bypass_network(self) -> bool:
        return self.allow_offline.get_active()

    def can_advance_from_network(self) -> bool:
        return bool(self.network_status.get("ready")) or self.can_bypass_network()

    def can_finish(self) -> bool:
        return self.can_advance_from_network()

    def refresh_network(self) -> None:
        try:
            status = read_network_status()
        except Exception as exc:
            status = {"ready": False, "progress": 0, "summary": "Unable to read network status", "last_error": str(exc)}
        self.network_status = status
        self.network_label.set_text(f"{status['summary']} ({status['progress']}%)")
        self.network_progress.set_fraction(status["progress"] / 100.0)
        if status.get("last_error"):
            self.set_status(f"Network status: {status['last_error']}")
        elif status["ready"]:
            self.set_status("Tor connection is ready.")
        else:
            self.set_status("Waiting for Tor to become ready.")
        self.update_navigation()

    def refresh_persistence(self) -> None:
        if self.persistence is None:
            self.persistence_label.set_text("Persistence backend unavailable.")
            self.update_persistence_actions({})
            return
        try:
            state = self.persistence.get_state()
        except Exception as exc:
            self.persistence_label.set_text(f"Persistence backend unavailable: {exc}")
            self.update_persistence_actions({})
            return
        self.persistence_label.set_text(self.render_persistence_state(state))
        self.update_persistence_actions(state)

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
        busy = bool(state.get("busy"))
        can_create = bool(state.get("can_create"))
        self.persistence_create.set_sensitive(can_create and not busy)
        self.persistence_unlock.set_sensitive(created and not unlocked and not busy)
        self.persistence_lock.set_sensitive(unlocked and not busy)
        self.persistence_repair.set_sensitive(unlocked and not busy)

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
        self.refresh_network()

    def on_allow_offline_toggled(self, _button: Gtk.CheckButton) -> None:
        if self.allow_offline.get_active():
            self.set_status("Offline bypass enabled. You can continue without Tor.")
        else:
            self.set_status("Offline bypass disabled.")
        self.update_navigation()

    def on_create_persistence(self, _button: Gtk.Button) -> None:
        if self.persistence is None:
            self.persistence_label.set_text("Persistence backend unavailable.")
            return
        try:
            response = self.persistence.create(self.persistence_password.get_text())
        except Exception as exc:
            self.set_status(f"Persistence create failed: {exc}")
            return
        self.handle_persistence_response("create", response)

    def on_unlock_persistence(self, _button: Gtk.Button) -> None:
        if self.persistence is None:
            self.persistence_label.set_text("Persistence backend unavailable.")
            return
        try:
            response = self.persistence.unlock(self.persistence_password.get_text())
        except Exception as exc:
            self.set_status(f"Persistence unlock failed: {exc}")
            return
        self.handle_persistence_response("unlock", response)

    def on_lock_persistence(self, _button: Gtk.Button) -> None:
        if self.persistence is None:
            self.persistence_label.set_text("Persistence backend unavailable.")
            return
        try:
            response = self.persistence.lock()
        except Exception as exc:
            self.set_status(f"Persistence lock failed: {exc}")
            return
        self.handle_persistence_response("lock", response)

    def on_repair_persistence(self, _button: Gtk.Button) -> None:
        if self.persistence is None:
            self.persistence_label.set_text("Persistence backend unavailable.")
            return
        try:
            response = self.persistence.repair()
        except Exception as exc:
            self.set_status(f"Persistence repair failed: {exc}")
            return
        self.handle_persistence_response("repair", response)

    def handle_persistence_response(self, action: str, response: dict) -> None:
        self.persistence_label.set_text(self.render_persistence_state(response))
        self.update_persistence_actions(response)
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
        if self.page_index == 0 and not self.apply_locale():
            return
        if self.page_index == 1 and not self.apply_keyboard():
            return
        if self.page_index < len(self.pages) - 1:
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
            self.set_status("Greeter state saved, but GDM session control is unavailable.")
            return
        self.set_sensitive(False)
        self.set_status("Starting the live session...")
        self.arm_session_start_timeout()
        try:
            self.gdm_client.start_session()
        except Exception as exc:
            self.clear_session_start_timeout()
            self.set_sensitive(True)
            self.set_status(f"Failed to start the live session: {exc}")

    def update_navigation(self) -> None:
        self.back_button.set_sensitive(self.page_index > 0)
        self.next_button.set_visible(self.page_index < len(self.pages) - 1)
        if self.page_index == 2:
            self.next_button.set_sensitive(self.can_advance_from_network())
        else:
            self.next_button.set_sensitive(True)
        self.finish_button.set_visible(self.page_index == len(self.pages) - 1)
        self.finish_button.set_sensitive(self.can_finish())

    def poll_runtime(self) -> bool:
        self.refresh_network()
        self.refresh_persistence()
        return True

    def arm_session_start_timeout(self) -> None:
        self.clear_session_start_timeout()
        self.session_start_timeout_id = GLib.timeout_add_seconds(15, self.on_session_start_timeout)

    def clear_session_start_timeout(self) -> None:
        if self.session_start_timeout_id:
            GLib.source_remove(self.session_start_timeout_id)
            self.session_start_timeout_id = 0

    def on_session_start_timeout(self) -> bool:
        self.session_start_timeout_id = 0
        self.set_sensitive(True)
        self.set_status("Live session start timed out.")
        return GLib.SOURCE_REMOVE

    def on_session_opened(self) -> None:
        self.clear_session_start_timeout()
        self.close()

    def on_session_problem(self, problem: str) -> None:
        self.clear_session_start_timeout()
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
