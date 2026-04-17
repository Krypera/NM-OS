from gi.repository import Gtk
from nmos_common.system_settings import PROFILE_METADATA

from nmos_control_center.panels.utils import labelled_control, page, string_dropdown


def build(window) -> Gtk.Widget:
    window.profile_combo = string_dropdown([PROFILE_METADATA[key]["label"] for key in window.profile_values])
    window.profile_combo.connect("notify::selected", window.on_profile_preview_changed)
    window.profile_summary = Gtk.Label(xalign=0)
    window.profile_summary.set_wrap(True)
    window.profile_guidance = Gtk.Label(xalign=0)
    window.profile_guidance.set_wrap(True)
    window.profile_guidance.add_css_class("dim-label")
    window.profile_tradeoff = Gtk.Label(xalign=0)
    window.profile_tradeoff.set_wrap(True)
    window.profile_tradeoff.add_css_class("dim-label")
    window.profile_details = Gtk.Label(xalign=0)
    window.profile_details.set_wrap(True)
    window.profile_meter_label = Gtk.Label(xalign=0)
    window.profile_meter_label.set_wrap(True)
    window.profile_meter_label.add_css_class("dim-label")
    window.profile_shift_label = Gtk.Label(xalign=0)
    window.profile_shift_label.set_wrap(True)
    window.profile_shift_label.add_css_class("dim-label")
    window.change_timing_label = Gtk.Label(xalign=0)
    window.change_timing_label.set_wrap(True)
    window.change_detail_label = Gtk.Label(xalign=0)
    window.change_detail_label.set_wrap(True)
    window.change_detail_label.add_css_class("dim-label")
    window.pending_reboot_label = Gtk.Label(xalign=0)
    window.pending_reboot_label.set_wrap(True)

    window.vault_auto_lock_combo = string_dropdown([label for _value, label in window.VAULT_AUTO_LOCK_OPTIONS])
    window.vault_auto_lock_combo.connect("notify::selected", window.on_draft_settings_changed)
    window.vault_auto_lock_change_explanation = Gtk.Label(xalign=0)
    window.vault_auto_lock_change_explanation.set_wrap(True)
    window.vault_auto_lock_change_explanation.add_css_class("dim-label")
    window.vault_unlock_on_login = Gtk.Switch()
    window.vault_unlock_on_login.connect("notify::active", window.on_draft_settings_changed)
    window.vault_unlock_change_explanation = Gtk.Label(xalign=0)
    window.vault_unlock_change_explanation.set_wrap(True)
    window.vault_unlock_change_explanation.add_css_class("dim-label")
    window.vault_explanation = Gtk.Label(xalign=0)
    window.vault_explanation.set_wrap(True)
    window.vault_explanation.add_css_class("dim-label")
    window.vault_passphrase_entry = Gtk.Entry()
    window.vault_passphrase_entry.set_visibility(False)
    window.vault_passphrase_entry.set_placeholder_text("Enter a vault passphrase to check strength")
    window.vault_passphrase_entry.connect("changed", window.on_vault_passphrase_changed)
    window.vault_passphrase_strength = Gtk.Label(xalign=0)
    window.vault_passphrase_strength.set_wrap(True)
    window.vault_passphrase_strength.add_css_class("dim-label")
    
    window.brave_switch = Gtk.Switch()
    window.brave_switch.connect("notify::active", window.on_draft_settings_changed)
    window.brave_change_explanation = Gtk.Label(xalign=0)
    window.brave_change_explanation.set_wrap(True)
    window.brave_change_explanation.add_css_class("dim-label")
    window.profile_change_explanation = Gtk.Label(xalign=0)
    window.profile_change_explanation.set_wrap(True)
    window.profile_change_explanation.add_css_class("dim-label")
    window.comfort_mode_button = Gtk.Button(label="Apply Comfort Mode")
    window.comfort_mode_button.connect("clicked", window.on_apply_comfort_mode)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)

    profile_page = page(
        "Security & Profiles",
        "Pick a security posture, then refine it with advanced pages if you want more control.",
        [
            labelled_control(
                "Security profile",
                "Balanced is recommended. Other profiles trade comfort for stronger or lighter restrictions.",
                window.profile_combo,
            ),
            Gtk.Label(
                label="Comfort Mode quickly switches to the Relaxed baseline while keeping your existing overrides.",
                xalign=0,
                wrap=True,
            ),
            window.comfort_mode_button,
            window.profile_change_explanation,
            window.profile_summary,
            window.profile_guidance,
            window.profile_tradeoff,
            window.profile_meter_label,
            window.profile_shift_label,
            window.profile_details,
            window.change_timing_label,
            window.change_detail_label,
            window.pending_reboot_label,
        ],
    )

    vault_page = page(
        "Vault",
        "Save your preferred encrypted vault behavior.",
        [
            labelled_control(
                "Auto-lock",
                "Choose how quickly the encrypted vault should relock after inactivity.",
                window.vault_auto_lock_combo,
            ),
            window.vault_auto_lock_change_explanation,
            labelled_control(
                "Unlock on login",
                "Keep this off unless you explicitly want convenience ahead of stronger separation.",
                window.vault_unlock_on_login,
            ),
            window.vault_unlock_change_explanation,
            labelled_control(
                "Vault passphrase check",
                "Use at least 12 chars with upper/lowercase, number, and special character.",
                window.vault_passphrase_entry,
            ),
            window.vault_passphrase_strength,
            window.vault_explanation,
        ],
    )
    
    browser_page = page(
        "Privacy Extras",
        "",
        [
            labelled_control(
                "Allow Brave Browser",
                "Brave stays hidden unless the build enables it and you allow it here.",
                window.brave_switch,
            ),
            window.brave_change_explanation,
        ]
    )

    box.append(profile_page)
    box.append(vault_page)
    box.append(browser_page)

    return box
