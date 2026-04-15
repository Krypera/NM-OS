from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.sandbox_combo = string_dropdown([label for _v, label in window.SANDBOX_OPTIONS])
    window.sandbox_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.sandbox_preset_combo = string_dropdown([label for _v, label in window.APP_SANDBOX_PRESET_OPTIONS])
    window.sandbox_preset_apply = Gtk.Button(label="Apply preset")
    window.sandbox_preset_apply.connect("clicked", window.on_apply_sandbox_preset)
    window.default_browser_combo = string_dropdown([label for _v, label in window.DEFAULT_BROWSER_OPTIONS])
    window.default_browser_combo.connect("notify::selected", window.on_draft_settings_changed)

    window.apps_explanation = Gtk.Label(xalign=0)
    window.apps_explanation.set_wrap(True)
    window.apps_explanation.add_css_class("dim-label")
    window.default_browser_change_explanation = Gtk.Label(xalign=0)
    window.default_browser_change_explanation.set_wrap(True)
    window.default_browser_change_explanation.add_css_class("dim-label")
    window.sandbox_change_explanation = Gtk.Label(xalign=0)
    window.sandbox_change_explanation.set_wrap(True)
    window.sandbox_change_explanation.add_css_class("dim-label")
    window.app_overrides_change_explanation = Gtk.Label(xalign=0)
    window.app_overrides_change_explanation.set_wrap(True)
    window.app_overrides_change_explanation.add_css_class("dim-label")
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
            window.default_browser_change_explanation,
            labelled_control(
                "Default app isolation",
                "Focused is the default middle ground between broad access and strict confinement.",
                window.sandbox_combo,
            ),
            window.sandbox_change_explanation,
            labelled_control(
                "Sandbox preset",
                "Secure tightens file access, Balanced keeps inheritance, Compatible prioritizes compatibility.",
                window.sandbox_preset_combo,
            ),
            window.sandbox_preset_apply,
            Gtk.Label(label="Per-app overrides", xalign=0),
            Gtk.Label(
                label="Choose filesystem, network, and device profiles per Flatpak app. Inherit uses the default isolation profile.",
                xalign=0,
                wrap=True,
            ),
            Gtk.Label(label="Each row: Filesystem | Network | Devices", xalign=0),
            window.app_overrides_change_explanation,
            window.app_overrides_refresh,
            window.app_overrides_empty,
            window.app_overrides_list,
            window.apps_explanation,
        ],
    )
