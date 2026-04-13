from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.theme_profile_combo = string_dropdown([label for _v, label in window.THEME_PROFILE_OPTIONS])
    window.accent_combo = string_dropdown([label for _v, label in window.ACCENT_OPTIONS])
    window.density_combo = string_dropdown([label for _v, label in window.DENSITY_OPTIONS])
    window.motion_combo = string_dropdown([label for _v, label in window.MOTION_OPTIONS])

    for combo in (window.theme_profile_combo, window.accent_combo, window.density_combo, window.motion_combo):
        combo.connect("notify::selected", window.on_theme_preview_changed)

    return page(
        "Appearance",
        "NM-OS uses a retro-futuristic theme language with limited, intentional customization.",
        [
            labelled_control("Theme profile", "Switch between the three supported NM-OS looks.", window.theme_profile_combo),
            labelled_control("Accent", "Accents are intentionally limited to keep the system cohesive.", window.accent_combo),
            labelled_control("Density", "Comfortable is easier to read; compact fits more information.", window.density_combo),
            labelled_control("Motion", "Reduced motion lowers distraction while keeping the interface responsive.", window.motion_combo),
        ],
    )
