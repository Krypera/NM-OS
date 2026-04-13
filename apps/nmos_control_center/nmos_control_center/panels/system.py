from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.device_policy_combo = string_dropdown([label for _v, label in window.DEVICE_POLICY_OPTIONS])
    window.device_policy_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.logging_combo = string_dropdown([label for _v, label in window.LOGGING_OPTIONS])
    window.logging_combo.connect("notify::selected", window.on_draft_settings_changed)

    window.system_explanation = Gtk.Label(xalign=0)
    window.system_explanation.set_wrap(True)
    window.system_explanation.add_css_class("dim-label")

    window.enforcement_status_label = Gtk.Label(xalign=0)
    window.enforcement_status_label.set_wrap(True)
    window.enforcement_status_label.add_css_class("dim-label")

    return page(
        "System & Recovery",
        "Control removable-media behavior, logging posture, and how quickly you can get back to a clean profile.",
        [
            labelled_control(
                "Device policy",
                "Prompt is the recommended baseline for external devices and removable media.",
                window.device_policy_combo,
            ),
            labelled_control(
                "Logging policy",
                "Minimal keeps diagnostics useful without retaining more than necessary.",
                window.logging_combo,
            ),
            window.system_explanation,
            Gtk.Label(label="Enforcement status", xalign=0),
            window.enforcement_status_label,
        ],
    )
