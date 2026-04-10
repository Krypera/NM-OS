from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from nmos_common.boot_mode import MODE_COMPAT, MODE_FLEXIBLE, MODE_OFFLINE, MODE_RECOVERY, MODE_STRICT
from nmos_common.i18n import display_language_name, resolve_supported_locale


def _combo(values: list[str]) -> Gtk.DropDown:
    model = Gtk.StringList.new(values)
    return Gtk.DropDown(model=model)


def _page(window, page_key: str, title_text: str, subtitle_text: str, control: Gtk.Widget) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    title = Gtk.Label(label=title_text, xalign=0)
    title.add_css_class("title-3")
    subtitle = Gtk.Label(label=subtitle_text, xalign=0)
    setattr(window, f"{page_key}_title_label", title)
    setattr(window, f"{page_key}_subtitle_label", subtitle)
    box.append(title)
    box.append(subtitle)
    box.append(control)
    return box


def _network_page(window) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.network_title_label = Gtk.Label(label="Network", xalign=0)
    window.network_title_label.add_css_class("title-3")
    box.append(window.network_title_label)
    box.append(window.network_label)
    box.append(window.network_progress)
    box.append(window.network_refresh)
    box.append(window.allow_offline)
    return box


def _persistence_page(window) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.persistence_title_label = Gtk.Label(label="Persistence", xalign=0)
    window.persistence_title_label.add_css_class("title-3")
    box.append(window.persistence_title_label)
    box.append(window.persistence_label)
    box.append(window.persistence_password)
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    actions.append(window.persistence_create)
    actions.append(window.persistence_unlock)
    actions.append(window.persistence_lock)
    actions.append(window.persistence_repair)
    box.append(actions)
    return box


def build_ui(window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    root.set_margin_top(24)
    root.set_margin_bottom(24)
    root.set_margin_start(24)
    root.set_margin_end(24)

    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    window.header_title_label = Gtk.Label(label="NM-OS")
    window.header_title_label.add_css_class("title-1")
    window.header_title_label.set_xalign(0)
    window.header_subtitle_label = Gtk.Label(xalign=0)
    window.mode_banner = Gtk.Label(xalign=0)
    window.mode_banner.add_css_class("caption")
    header.append(window.header_title_label)
    header.append(window.header_subtitle_label)
    header.append(window.mode_banner)
    root.append(header)

    window.session_status = Gtk.Label(xalign=0)
    window.session_status.add_css_class("caption")
    root.append(window.session_status)

    window.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    window.stack.set_vexpand(True)

    window.language_combo = _combo([display_language_name(locale) for locale in window.language_values])
    window.keyboard_combo = _combo(["us", "tr", "de", "fr"])
    window.network_progress = Gtk.ProgressBar()
    window.network_label = Gtk.Label(xalign=0)
    window.network_refresh = Gtk.Button()
    window.network_refresh.connect("clicked", window.on_refresh_network)
    window.allow_offline = Gtk.CheckButton()
    window.allow_offline.connect("toggled", window.on_allow_offline_toggled)

    window.persistence_label = Gtk.Label(xalign=0)
    window.persistence_password = Gtk.PasswordEntry()
    window.persistence_create = Gtk.Button()
    window.persistence_unlock = Gtk.Button()
    window.persistence_lock = Gtk.Button()
    window.persistence_repair = Gtk.Button()
    window.persistence_create.connect("clicked", window.on_create_persistence)
    window.persistence_unlock.connect("clicked", window.on_unlock_persistence)
    window.persistence_lock.connect("clicked", window.on_lock_persistence)
    window.persistence_repair.connect("clicked", window.on_repair_persistence)

    window.page_widgets = {
        "language": _page(window, "language", "Language", "Choose the session language.", window.language_combo),
        "keyboard": _page(window, "keyboard", "Keyboard", "Choose the keyboard layout.", window.keyboard_combo),
        "network": _network_page(window),
        "persistence": _persistence_page(window),
    }

    for index, key in enumerate(window.page_order):
        window.stack.add_titled(window.page_widgets[key], f"page-{index}", f"Page {index + 1}")

    root.append(window.stack)

    nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    window.back_button = Gtk.Button()
    window.next_button = Gtk.Button()
    window.finish_button = Gtk.Button()
    window.back_button.connect("clicked", window.on_back)
    window.next_button.connect("clicked", window.on_next)
    window.finish_button.connect("clicked", window.on_finish)
    nav.append(window.back_button)
    nav.append(window.next_button)
    nav.append(window.finish_button)
    root.append(nav)

    window.set_content(root)


def mode_title(window) -> str:
    return {
        MODE_STRICT: window.tr("Strict"),
        MODE_FLEXIBLE: window.tr("Flexible"),
        MODE_OFFLINE: window.tr("Offline"),
        MODE_RECOVERY: window.tr("Recovery"),
        MODE_COMPAT: window.tr("Hardware Compatibility"),
    }.get(window.boot_mode, window.tr("Strict"))


def mode_description(window) -> str:
    if window.boot_mode == MODE_FLEXIBLE:
        return window.tr("Tor-first with a more relaxed onboarding flow.")
    if window.boot_mode == MODE_OFFLINE:
        return window.tr("Networking is intentionally disabled for this session.")
    if window.boot_mode == MODE_RECOVERY:
        return window.tr("Recovery-first session with networking intentionally disabled.")
    if window.boot_mode == MODE_COMPAT:
        return window.tr("Compatibility boot options are enabled while keeping strict network policy.")
    return window.tr("Tor-first strict profile is active.")


def is_network_disabled_mode(window) -> bool:
    return window.boot_mode in {MODE_OFFLINE, MODE_RECOVERY}


def resolve_page_order(window) -> list[str]:
    if window.boot_mode == MODE_RECOVERY:
        return ["persistence", "language", "keyboard", "network"]
    return ["language", "keyboard", "network", "persistence"]


def current_page_key(window) -> str:
    return window.page_order[window.page_index]


def current_language_code(window) -> str:
    selected = window.language_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.language_values):
        window.language_combo.set_selected(0)
        return window.language_values[0]
    return window.language_values[selected]


def current_language_name(window) -> str:
    return display_language_name(current_language_code(window))


def action_label(window, action: str) -> str:
    return window.tr(action.capitalize()).lower()


def apply_translations(window) -> None:
    window.set_title(window.tr("NM-OS Greeter"))
    window.header_subtitle_label.set_text(window.tr("Prepare your session before entering the desktop."))
    window.language_title_label.set_text(window.tr("Language"))
    window.language_subtitle_label.set_text(window.tr("Choose the session language."))
    window.keyboard_title_label.set_text(window.tr("Keyboard"))
    window.keyboard_subtitle_label.set_text(window.tr("Choose the keyboard layout."))
    window.network_title_label.set_text(window.tr("Network"))
    window.persistence_title_label.set_text(window.tr("Persistence"))
    window.network_refresh.set_label(window.tr("Refresh network status"))
    window.allow_offline.set_label(window.tr("Continue to desktop while network stays blocked"))
    window.persistence_create.set_label(window.tr("Create"))
    window.persistence_unlock.set_label(window.tr("Unlock"))
    window.persistence_lock.set_label(window.tr("Lock"))
    window.persistence_repair.set_label(window.tr("Repair"))
    window.back_button.set_label(window.tr("Back"))
    window.next_button.set_label(window.tr("Next"))
    window.finish_button.set_label(window.tr("Finish"))
    window.mode_banner.set_text(
        window.tr("Mode: {mode} - {description}", mode=mode_title(window), description=mode_description(window))
    )
    if window.persistence_init_error:
        window.persistence_label.set_text(
            window.tr(
                "Persistence backend unavailable: {error}",
                error=window.translate_message(window.persistence_init_error),
            )
        )
    elif window.persistence_state:
        window.persistence_label.set_text(window.render_persistence_state(window.persistence_state))


def apply_mode_ui_policy(window) -> None:
    window.mode_banner.set_text(
        window.tr("Mode: {mode} - {description}", mode=mode_title(window), description=mode_description(window))
    )
    if is_network_disabled_mode(window):
        window.allow_offline.set_active(True)
        window.allow_offline.set_sensitive(False)
        window.network_refresh.set_sensitive(False)
    elif window.boot_mode == MODE_FLEXIBLE:
        window.allow_offline.set_active(True)


def _select_string(dropdown: Gtk.DropDown, value: str) -> None:
    model = dropdown.get_model()
    for index in range(model.get_n_items()):
        if model.get_string(index) == value:
            dropdown.set_selected(index)
            return


def _select_language(window, locale: str) -> None:
    resolved = resolve_supported_locale(locale)
    for index, value in enumerate(window.language_values):
        if value == resolved:
            window.language_combo.set_selected(index)
            return
    window.language_combo.set_selected(0)


def current_string(dropdown: Gtk.DropDown) -> str:
    model = dropdown.get_model()
    selected = dropdown.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= model.get_n_items():
        if model.get_n_items() == 0:
            return ""
        dropdown.set_selected(0)
        selected = 0
    return model.get_string(selected)


def restore_state(window) -> None:
    locale = window.state.get("locale", "en_US.UTF-8")
    keyboard = window.state.get("keyboard", "us")
    _select_language(window, locale)
    _select_string(window.keyboard_combo, keyboard)
    if is_network_disabled_mode(window):
        window.allow_offline.set_active(True)
    elif window.boot_mode == MODE_FLEXIBLE and "allow_offline" not in window.state:
        window.allow_offline.set_active(True)
    else:
        window.allow_offline.set_active(bool(window.state.get("allow_offline", False)))


def set_status(window, text: str, *, source: str = "event", force: bool = True) -> None:
    if not force and source == "network" and window.status_source not in {"", "network"}:
        return
    window.status_source = source
    window.session_status.set_text(text)


def collect_state(window) -> dict:
    return {
        "locale": current_language_code(window),
        "keyboard": current_string(window.keyboard_combo),
        "allow_offline": window.allow_offline.get_active(),
    }


def can_bypass_network(window) -> bool:
    if is_network_disabled_mode(window):
        return True
    if window.boot_mode == MODE_FLEXIBLE:
        return True
    return window.allow_offline.get_active()


def can_advance_from_network(window) -> bool:
    if is_network_disabled_mode(window):
        return True
    return bool(window.network_status.get("ready")) or can_bypass_network(window)


def can_finish(window) -> bool:
    if window.persistence_state.get("busy") or window.persistence_action_in_progress or window.persistence_refresh_in_progress:
        return False
    return can_advance_from_network(window)


def update_navigation(window) -> None:
    window.back_button.set_sensitive(window.page_index > 0)
    window.next_button.set_visible(window.page_index < len(window.page_order) - 1)
    if current_page_key(window) == "network":
        window.next_button.set_sensitive(can_advance_from_network(window))
    else:
        window.next_button.set_sensitive(True)
    window.finish_button.set_visible(window.page_index == len(window.page_order) - 1)
    window.finish_button.set_sensitive(can_finish(window))
