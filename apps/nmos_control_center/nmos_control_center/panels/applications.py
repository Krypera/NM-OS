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
    window.app_overrides_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    window.app_overrides_empty = Gtk.Label(xalign=0)
    window.app_overrides_empty.set_wrap(True)
    window.app_overrides_empty.add_css_class("dim-label")
    window.app_overrides_refresh = Gtk.Button(label="Refresh app list")
    window.app_overrides_refresh.connect("clicked", window.on_refresh_app_list)

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
            Gtk.Label(label="Per-app overrides", xalign=0),
            Gtk.Label(
                label="Choose a filesystem profile per Flatpak app. Inherit uses the default isolation profile.",
                xalign=0,
                wrap=True,
            ),
            window.app_overrides_refresh,
            window.app_overrides_empty,
            window.app_overrides_list,
            window.apps_explanation,
        ],
    )
