from gi.repository import Gtk

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.device_policy_combo = string_dropdown([label for _v, label in window.DEVICE_POLICY_OPTIONS])
    window.device_policy_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.device_policy_change_explanation = Gtk.Label(xalign=0)
    window.device_policy_change_explanation.set_wrap(True)
    window.device_policy_change_explanation.add_css_class("dim-label")
    window.logging_combo = string_dropdown([label for _v, label in window.LOGGING_OPTIONS])
    window.logging_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.logging_change_explanation = Gtk.Label(xalign=0)
    window.logging_change_explanation.set_wrap(True)
    window.logging_change_explanation.add_css_class("dim-label")

    window.system_explanation = Gtk.Label(xalign=0)
    window.system_explanation.set_wrap(True)
    window.system_explanation.add_css_class("dim-label")

    window.enforcement_status_label = Gtk.Label(xalign=0)
    window.enforcement_status_label.set_wrap(True)
    window.enforcement_status_label.add_css_class("dim-label")
    window.privacy_dashboard_label = Gtk.Label(xalign=0)
    window.privacy_dashboard_label.set_wrap(True)
    window.privacy_dashboard_label.add_css_class("dim-label")
    window.trust_chain_label = Gtk.Label(xalign=0)
    window.trust_chain_label.set_wrap(True)
    window.trust_chain_label.add_css_class("dim-label")
    window.emergency_lockdown_button = Gtk.Button(label="Emergency Lockdown")
    window.emergency_lockdown_button.add_css_class("destructive-action")
    window.emergency_lockdown_button.connect("clicked", window.on_emergency_lockdown)
    window.trust_chain_refresh_button = Gtk.Button(label="Refresh trust data")
    window.trust_chain_refresh_button.connect("clicked", window.on_refresh_trust_chain)

    return page(
        "System & Recovery",
        "Control removable-media behavior, logging posture, and how quickly you can get back to a clean profile.",
        [
            labelled_control(
                "Device policy",
                "Prompt is the recommended baseline for external devices and removable media.",
                window.device_policy_combo,
            ),
            window.device_policy_change_explanation,
            labelled_control(
                "Logging policy",
                "Minimal keeps diagnostics useful without retaining more than necessary.",
                window.logging_combo,
            ),
            window.logging_change_explanation,
            window.system_explanation,
            Gtk.Label(label="Privacy dashboard", xalign=0),
            window.privacy_dashboard_label,
            window.emergency_lockdown_button,
            Gtk.Label(label="Enforcement status", xalign=0),
            window.enforcement_status_label,
            Gtk.Label(label="Trust chain viewer", xalign=0),
            window.trust_chain_label,
            window.trust_chain_refresh_button,
        ],
    )
