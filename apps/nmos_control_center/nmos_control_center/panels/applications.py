from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.sandbox_combo = string_dropdown([label for _v, label in window.SANDBOX_OPTIONS])
    window.sandbox_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.default_browser_combo = string_dropdown([label for _v, label in window.DEFAULT_BROWSER_OPTIONS])
    window.default_browser_combo.connect("notify::selected", window.on_draft_settings_changed)

    window.apps_explanation = Gtk.Label(xalign=0)
    window.apps_explanation.set_wrap(True)
    window.apps_explanation.add_css_class("dim-label")

    return page(
        "Apps & Permissions",
        "Manage app permissions and isolation.",
        [
            labelled_control(
                "Default browser",
                "Choose the browser NM-OS should open for web links.",
                window.default_browser_combo,
            ),
            labelled_control(
                "Default app isolation",
                "Focused is the default middle ground between broad access and strict confinement.",
                window.sandbox_combo,
            ),
            Gtk.Label(
                label="Per-app overrides will land later. This first slice keeps the default policy readable and easy to change.",
                xalign=0,
                wrap=True,
            ),
            window.apps_explanation,
        ],
    )
