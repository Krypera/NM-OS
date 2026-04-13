from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.network_combo = string_dropdown([label for _value, label in window.NETWORK_OPTIONS])
    window.network_combo.connect("notify::selected", window.on_draft_settings_changed)

    window.privacy_explanation = Gtk.Label(xalign=0)
    window.privacy_explanation.set_wrap(True)
    window.privacy_explanation.add_css_class("dim-label")

    return page(
        "Network & Internet",
        "Choose how networking behaves.",
        [
            labelled_control("Network policy", "Tor-first keeps the safest baseline.", window.network_combo),
            window.privacy_explanation,
        ],
    )
