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
    window.ram_wipe_combo = string_dropdown([label for _v, label in window.RAM_WIPE_OPTIONS])
    window.ram_wipe_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.ram_wipe_change_explanation = Gtk.Label(xalign=0)
    window.ram_wipe_change_explanation.set_wrap(True)
    window.ram_wipe_change_explanation.add_css_class("dim-label")

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
    window.recovery_status_label = Gtk.Label(xalign=0)
    window.recovery_status_label.set_wrap(True)
    window.recovery_status_label.add_css_class("dim-label")
    window.ram_wipe_status_label = Gtk.Label(xalign=0)
    window.ram_wipe_status_label.set_wrap(True)
    window.ram_wipe_status_label.add_css_class("dim-label")
    window.emergency_lockdown_button = Gtk.Button(label="Emergency Lockdown")
    window.emergency_lockdown_button.add_css_class("destructive-action")
    window.emergency_lockdown_button.connect("clicked", window.on_emergency_lockdown)
    window.trust_chain_refresh_button = Gtk.Button(label="Refresh trust data")
    window.trust_chain_refresh_button.connect("clicked", window.on_refresh_trust_chain)
    window.create_diagnostics_bundle_button = Gtk.Button(label="Create diagnostics bundle")
    window.create_diagnostics_bundle_button.connect("clicked", window.on_create_diagnostics_bundle)
    window.open_user_guides_button = Gtk.Button(label="Open User Guides")
    window.open_user_guides_button.connect("clicked", window.on_open_user_guides)
    window.snapshot_rollback_button = Gtk.Button(label="Rollback last settings")
    window.snapshot_rollback_button.connect("clicked", window.on_rollback_settings_snapshot)
    window.update_channel_combo = string_dropdown([label for _v, label in window.UPDATE_CHANNEL_OPTIONS])
    window.update_channel_combo.connect("notify::selected", window.on_update_channel_changed)
    window.update_status_label = Gtk.Label(xalign=0)
    window.update_status_label.set_wrap(True)
    window.update_status_label.add_css_class("dim-label")
    window.update_check_button = Gtk.Button(label="Check updates")
    window.update_check_button.connect("clicked", window.on_check_updates)
    window.update_apply_button = Gtk.Button(label="Apply update")
    window.update_apply_button.connect("clicked", window.on_apply_update)
    window.update_rollback_button = Gtk.Button(label="Rollback")
    window.update_rollback_button.connect("clicked", window.on_rollback_update)

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
            labelled_control(
                "RAM wipe policy",
                "Balanced enables kernel memory scrubbing with moderate overhead; Strict maximizes hygiene.",
                window.ram_wipe_combo,
            ),
            window.ram_wipe_change_explanation,
            window.ram_wipe_status_label,
            window.system_explanation,
            Gtk.Label(label="Privacy dashboard", xalign=0),
            window.privacy_dashboard_label,
            window.emergency_lockdown_button,
            Gtk.Label(label="Enforcement status", xalign=0),
            window.enforcement_status_label,
            Gtk.Label(label="Trust chain viewer", xalign=0),
            window.trust_chain_label,
            window.trust_chain_refresh_button,
            Gtk.Label(label="Recovery actions", xalign=0),
            window.recovery_status_label,
            window.open_user_guides_button,
            window.create_diagnostics_bundle_button,
            window.snapshot_rollback_button,
            Gtk.Label(label="Update center", xalign=0),
            labelled_control(
                "Release channel",
                "Choose the update stream. Stable favors predictability, beta and nightly move faster.",
                window.update_channel_combo,
            ),
            window.update_status_label,
            window.update_check_button,
            window.update_apply_button,
            window.update_rollback_button,
        ],
    )
