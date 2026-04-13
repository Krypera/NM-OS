from gi.repository import Gtk
from nmos_common.i18n import display_language_name

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.language_combo = string_dropdown([display_language_name(locale) for locale in window.language_values])
    window.language_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.keyboard_combo = string_dropdown(list(window.KEYBOARD_OPTIONS))
    window.keyboard_combo.connect("notify::selected", window.on_draft_settings_changed)

    return page(
        "Language & Region",
        "Adjust display language and keyboard defaults for new sessions.",
        [
            labelled_control(
                "Language",
                "English remains the source language and Spanish is included today.",
                window.language_combo,
            ),
            labelled_control(
                "Keyboard",
                "Choose the default keyboard layout for the next login.",
                window.keyboard_combo,
            ),
        ],
    )
