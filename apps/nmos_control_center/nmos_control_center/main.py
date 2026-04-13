from __future__ import annotations

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk
from nmos_common.i18n import (
    LANGUAGE_OPTIONS,
    explain_brave_visibility,
    explain_device_policy,
    explain_logging_policy,
    explain_network_policy,
    explain_sandbox_default,
    explain_vault_behavior,
    format_change_detail,
    format_posture_shift,
    posture_explanation_lines,
    posture_meter_lines,
    resolve_supported_locale,
    translate,
)
from nmos_common.settings_client import SettingsClient, SettingsClientError
from nmos_common.system_settings import (
    ACCENT_LABELS,
    DEFAULT_SYSTEM_SETTINGS,
    DENSITY_LABELS,
    MOTION_LABELS,
    PROFILE_METADATA,
    THEME_PROFILE_LABELS,
    compute_posture_score_shift,
    compute_posture_scores,
    derive_overrides_for_profile,
    describe_effective_change_details,
    describe_posture_preview,
    normalize_system_settings,
    setting_display_name,
)
from nmos_common.ui_theme import apply_window_theme, load_css

KEYBOARD_OPTIONS = ("us", "tr", "de", "fr")
NETWORK_OPTIONS = (
    ("tor", "Tor-first"),
    ("direct", "Direct network"),
    ("offline", "Offline"),
)
SANDBOX_OPTIONS = (
    ("standard", "Standard"),
    ("focused", "Focused"),
    ("strict", "Strict"),
)
DEVICE_POLICY_OPTIONS = (
    ("shared", "Shared devices"),
    ("prompt", "Prompt first"),
    ("locked", "Locked down"),
)
LOGGING_OPTIONS = (
    ("balanced", "Balanced"),
    ("minimal", "Minimal"),
    ("sealed", "Sealed"),
)
THEME_PROFILE_OPTIONS = tuple(THEME_PROFILE_LABELS.items())
ACCENT_OPTIONS = tuple(ACCENT_LABELS.items())
DENSITY_OPTIONS = tuple(DENSITY_LABELS.items())
MOTION_OPTIONS = tuple(MOTION_LABELS.items())
DEFAULT_BROWSER_OPTIONS = (
    ("firefox-esr", "Firefox"),
    ("chromium", "Chromium"),
    ("none", "No default browser"),
)
VAULT_AUTO_LOCK_OPTIONS = (
    ("0", "Manual lock"),
    ("5", "5 minutes"),
    ("15", "15 minutes"),
    ("30", "30 minutes"),
    ("60", "1 hour"),
)


from nmos_control_center.panels import applications, language, network, personalization, security, system


class ControlCenterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Control Center")
        self.set_default_size(1080, 720)
        self.client = SettingsClient(allow_local_fallback=False)
        self.backend_ready = True
        self.startup_error_message = ""
        try:
            self.settings = self.client.get_settings()
        except SettingsClientError as error:
            self.settings = dict(DEFAULT_SYSTEM_SETTINGS)
            self.backend_ready = False
            self.startup_error_message = self.format_backend_guidance(error)
        self.profile_values = list(PROFILE_METADATA)
        self.language_values = [locale for locale, _label in LANGUAGE_OPTIONS]
        
        self.KEYBOARD_OPTIONS = KEYBOARD_OPTIONS
        self.NETWORK_OPTIONS = NETWORK_OPTIONS
        self.SANDBOX_OPTIONS = SANDBOX_OPTIONS
        self.DEVICE_POLICY_OPTIONS = DEVICE_POLICY_OPTIONS
        self.LOGGING_OPTIONS = LOGGING_OPTIONS
        self.THEME_PROFILE_OPTIONS = THEME_PROFILE_OPTIONS
        self.ACCENT_OPTIONS = ACCENT_OPTIONS
        self.DENSITY_OPTIONS = DENSITY_OPTIONS
        self.MOTION_OPTIONS = MOTION_OPTIONS
        self.DEFAULT_BROWSER_OPTIONS = DEFAULT_BROWSER_OPTIONS
        self.VAULT_AUTO_LOCK_OPTIONS = VAULT_AUTO_LOCK_OPTIONS

        self.ui_locale = resolve_supported_locale(self.settings.get("locale", "en_US.UTF-8"))
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.root.set_margin_top(24)
        self.root.set_margin_bottom(24)
        self.root.set_margin_start(24)
        self.root.set_margin_end(24)
        self.build_ui()
        self.restore_settings()
        self.refresh_summary()
        if not self.backend_ready:
            self.apply_button.set_sensitive(False)
            self.reset_button.set_sensitive(False)
            prefix = f"{self.startup_error_message} " if self.startup_error_message else ""
            self.status_label.set_text(f"{prefix}Review mode only until service is reachable. Use Diagnostics for details.")
        self.set_content(self.root)

    def describe_backend_issue(self, error: SettingsClientError) -> str:
        if error.reason == "access_denied":
            return "Settings backend denied access. Sign in with an authorized session and retry."
        if error.reason == "backend_unavailable":
            return "Settings backend is unavailable. Retry in a moment or check the settings service health."
        if error.reason == "transport_error":
            return "Settings backend connection failed. Check runtime service status, then retry."
        if error.reason == "dbus_import_error":
            return "D-Bus runtime is unavailable on this system."
        return error.user_message()

    def backend_recovery_hint(self, error: SettingsClientError) -> str:
        if error.reason == "access_denied":
            return "Action: sign in with an admin-authorized session, then click Refresh."
        if error.reason == "backend_unavailable":
            return "Action: click Refresh. If it persists, run: systemctl status nmos-settings.service"
        if error.reason == "transport_error":
            return "Action: verify D-Bus and service health, then retry. Diagnostics can help."
        if error.reason == "dbus_import_error":
            return "Action: use review mode or safe mode until D-Bus is available."
        return "Action: retry, then open diagnostics if the problem continues."

    def format_backend_guidance(self, error: SettingsClientError) -> str:
        return f"{self.describe_backend_issue(error)} {self.backend_recovery_hint(error)}"

    def _selected_value(self, dropdown: Gtk.DropDown, values: list[str]) -> str:
        selected = dropdown.get_selected()
        if selected == Gtk.INVALID_LIST_POSITION or selected >= len(values):
            dropdown.set_selected(0)
            return values[0]
        return values[selected]

    def _set_dropdown_value(self, dropdown: Gtk.DropDown, values: list[str], value: str) -> None:
        try:
            dropdown.set_selected(values.index(value))
        except ValueError:
            dropdown.set_selected(0)

    def tr(self, source_text: str, **kwargs) -> str:
        return translate(self.ui_locale, source_text, **kwargs)

    def build_ui(self) -> None:
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = Gtk.Label(label="NM-OS Control Center", xalign=0)
        title.add_css_class("title-1")
        subtitle = Gtk.Label(
            label="Tune privacy, Appearance, and recovery behavior without leaving the desktop.",
            xalign=0,
        )
        subtitle.set_wrap(True)
        subtitle.add_css_class("dim-label")
        header.append(title)
        header.append(subtitle)
        self.root.append(header)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self.root.append(split)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.sidebar = Gtk.StackSidebar()
        self.sidebar.set_stack(self.stack)
        self.sidebar.set_vexpand(True)
        self.sidebar.set_size_request(240, -1)
        split.append(self.sidebar)
        split.append(self.stack)

        self.personalization_page = personalization.build(self)
        self.applications_page = applications.build(self)
        self.network_page = network.build(self)
        self.security_page = security.build(self)
        self.system_page = system.build(self)
        self.language_page = language.build(self)

        pages = [
            ("personalization", "Personalization", self.personalization_page),
            ("applications", "Applications", self.applications_page),
            ("network", "Network & Internet", self.network_page),
            ("security", "Security & Profiles", self.security_page),
            ("system", "System & Recovery", self.system_page),
            ("language", "Language & Region", self.language_page),
        ]
        for key, title_text, widget in pages:
            self.stack.add_titled(widget, key, title_text)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.refresh_button = Gtk.Button(label="Refresh")
        self.diagnostics_button = Gtk.Button(label="Diagnostics")
        self.reset_button = Gtk.Button(label="Reset To Profile")
        self.apply_button = Gtk.Button(label="Apply Changes")
        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_hexpand(True)
        self.status_label.set_wrap(True)
        self.status_label.add_css_class("dim-label")
        self.refresh_button.connect("clicked", self.on_refresh)
        self.diagnostics_button.connect("clicked", self.on_diagnostics)
        self.reset_button.connect("clicked", self.on_reset_to_profile)
        self.apply_button.connect("clicked", self.on_apply)
        actions.append(self.status_label)
        actions.append(self.refresh_button)
        actions.append(self.diagnostics_button)
        actions.append(self.reset_button)
        actions.append(self.apply_button)
        self.root.append(actions)

    def restore_settings(self) -> None:
        settings = self.settings
        profile = str(settings.get("active_profile", "balanced"))
        locale = resolve_supported_locale(settings.get("locale", "en_US.UTF-8"))
        keyboard = str(settings.get("keyboard", "us"))
        network_policy = str(settings.get("network_policy", "tor"))
        sandbox_default = str(settings.get("sandbox_default", "focused"))
        device_policy = str(settings.get("device_policy", "prompt"))
        logging_policy = str(settings.get("logging_policy", "minimal"))
        theme_profile = str(settings.get("ui_theme_profile", "nmos-classic"))
        accent = str(settings.get("ui_accent", "amber"))
        density = str(settings.get("ui_density", "comfortable"))
        motion = str(settings.get("ui_motion", "full"))
        default_browser = str(settings.get("default_browser", "firefox-esr"))
        vault = settings.get("vault", {})
        auto_lock = str(vault.get("auto_lock_minutes", 15))

        self._set_dropdown_value(self.profile_combo, self.profile_values, profile)
        self._set_dropdown_value(self.language_combo, self.language_values, locale)
        self._set_dropdown_value(self.keyboard_combo, list(KEYBOARD_OPTIONS), keyboard)
        self._set_dropdown_value(self.network_combo, [value for value, _label in NETWORK_OPTIONS], network_policy)
        self._set_dropdown_value(self.sandbox_combo, [value for value, _label in SANDBOX_OPTIONS], sandbox_default)
        self._set_dropdown_value(self.device_policy_combo, [value for value, _label in DEVICE_POLICY_OPTIONS], device_policy)
        self._set_dropdown_value(self.logging_combo, [value for value, _label in LOGGING_OPTIONS], logging_policy)
        self._set_dropdown_value(self.theme_profile_combo, [value for value, _label in THEME_PROFILE_OPTIONS], theme_profile)
        self._set_dropdown_value(self.accent_combo, [value for value, _label in ACCENT_OPTIONS], accent)
        self._set_dropdown_value(self.density_combo, [value for value, _label in DENSITY_OPTIONS], density)
        self._set_dropdown_value(self.motion_combo, [value for value, _label in MOTION_OPTIONS], motion)
        self._set_dropdown_value(self.default_browser_combo, [value for value, _label in DEFAULT_BROWSER_OPTIONS], default_browser)
        self._set_dropdown_value(self.vault_auto_lock_combo, [value for value, _label in VAULT_AUTO_LOCK_OPTIONS], auto_lock)
        self.brave_switch.set_active(bool(settings.get("allow_brave_browser", False)))
        self.vault_unlock_on_login.set_active(bool(vault.get("unlock_on_login", False)))
        self.ui_locale = locale
        self.preview_theme()

    def preview_theme(self) -> None:
        apply_window_theme(
            self.root,
            {
                "ui_theme_profile": self._selected_value(self.theme_profile_combo, [value for value, _label in THEME_PROFILE_OPTIONS]),
                "ui_accent": self._selected_value(self.accent_combo, [value for value, _label in ACCENT_OPTIONS]),
                "ui_density": self._selected_value(self.density_combo, [value for value, _label in DENSITY_OPTIONS]),
                "ui_motion": self._selected_value(self.motion_combo, [value for value, _label in MOTION_OPTIONS]),
            },
        )

    def collect_values(self) -> dict:
        return {
            "locale": self._selected_value(self.language_combo, self.language_values),
            "keyboard": self._selected_value(self.keyboard_combo, list(KEYBOARD_OPTIONS)),
            "network_policy": self._selected_value(self.network_combo, [value for value, _label in NETWORK_OPTIONS]),
            "allow_brave_browser": self.brave_switch.get_active(),
            "sandbox_default": self._selected_value(self.sandbox_combo, [value for value, _label in SANDBOX_OPTIONS]),
            "default_browser": self._selected_value(
                self.default_browser_combo,
                [value for value, _label in DEFAULT_BROWSER_OPTIONS],
            ),
            "vault": {
                "enabled": True,
                "auto_lock_minutes": int(
                    self._selected_value(self.vault_auto_lock_combo, [value for value, _label in VAULT_AUTO_LOCK_OPTIONS])
                ),
                "unlock_on_login": self.vault_unlock_on_login.get_active(),
            },
            "device_policy": self._selected_value(self.device_policy_combo, [value for value, _label in DEVICE_POLICY_OPTIONS]),
            "logging_policy": self._selected_value(self.logging_combo, [value for value, _label in LOGGING_OPTIONS]),
            "ui_theme_profile": self._selected_value(self.theme_profile_combo, [value for value, _label in THEME_PROFILE_OPTIONS]),
            "ui_accent": self._selected_value(self.accent_combo, [value for value, _label in ACCENT_OPTIONS]),
            "ui_density": self._selected_value(self.density_combo, [value for value, _label in DENSITY_OPTIONS]),
            "ui_motion": self._selected_value(self.motion_combo, [value for value, _label in MOTION_OPTIONS]),
        }

    def refresh_summary(self) -> None:
        profile = self._selected_value(self.profile_combo, self.profile_values)
        draft_values = self.collect_values()
        self.ui_locale = resolve_supported_locale(self._selected_value(self.language_combo, self.language_values))
        posture = describe_posture_preview(profile, {"active_profile": profile, **draft_values})
        draft_settings = normalize_system_settings(
            {
                "active_profile": profile,
                "overrides": derive_overrides_for_profile(profile, draft_values),
            }
        )
        self.profile_summary.set_text(self.tr(posture["summary"]))
        self.profile_guidance.set_text(self.tr(posture["ideal_for"]))
        self.profile_tradeoff.set_text(self.tr(posture["tradeoff"]))
        self.profile_meter_label.set_text("\n".join(posture_meter_lines(self.ui_locale, posture)))
        current_scores = compute_posture_scores(self.settings)
        shift = compute_posture_score_shift(current_scores, posture.get("scores", {}))
        self.profile_shift_label.set_text(format_posture_shift(self.ui_locale, shift))
        self.profile_details.set_text(
            "\n".join(f"- {line}" for line in posture_explanation_lines(self.ui_locale, posture))
        )
        effective_payload = {
            "active_profile": profile,
            "overrides": derive_overrides_for_profile(profile, draft_values),
        }
        change_details = describe_effective_change_details(effective_payload)
        immediate_details = change_details["immediate"]
        reboot_details = change_details["reboot"]
        immediate_labels = [self.tr(setting_display_name(str(item["key"]))) for item in immediate_details]
        reboot_labels = [self.tr(setting_display_name(str(item["key"]))) for item in reboot_details]
        if immediate_labels or reboot_labels:
            self.change_timing_label.set_text(
                "\n".join(
                    [
                        self.tr(
                            "Applies now: {changes}",
                            changes=", ".join(immediate_labels) if immediate_labels else self.tr("None"),
                        ),
                        self.tr(
                            "Applies after reboot: {changes}",
                            changes=", ".join(reboot_labels) if reboot_labels else self.tr("None"),
                        ),
                    ]
                )
            )
            detail_lines: list[str] = []
            if immediate_details:
                detail_lines.append(self.tr("Change details (now):"))
                detail_lines.extend(
                    f"- {format_change_detail(self.ui_locale, self.tr(setting_display_name(str(item['key']))), str(item['key']), item.get('from'), item.get('to'))}"
                    for item in immediate_details
                )
            if reboot_details:
                detail_lines.append(self.tr("Change details (after reboot):"))
                detail_lines.extend(
                    f"- {format_change_detail(self.ui_locale, self.tr(setting_display_name(str(item['key']))), str(item['key']), item.get('from'), item.get('to'))}"
                    for item in reboot_details
                )
            self.change_detail_label.set_text("\n".join(detail_lines))
        else:
            self.change_timing_label.set_text(self.tr("No changed settings in the current draft."))
            self.change_detail_label.set_text("")
        self.privacy_explanation.set_text(
            "\n".join(
                [
                    explain_network_policy(self.ui_locale, draft_values["network_policy"]),
                    explain_brave_visibility(
                        self.ui_locale,
                        bool(draft_values["allow_brave_browser"]),
                        str(draft_values["network_policy"]),
                    ),
                ]
            )
        )
        self.apps_explanation.set_text(
            explain_sandbox_default(self.ui_locale, str(draft_values["sandbox_default"]))
        )
        self.vault_explanation.set_text(
            "\n".join(explain_vault_behavior(self.ui_locale, draft_values["vault"]))
        )
        self.system_explanation.set_text(
            "\n".join(
                [
                    explain_device_policy(self.ui_locale, str(draft_values["device_policy"])),
                    explain_logging_policy(self.ui_locale, str(draft_values["logging_policy"])),
                ]
            )
        )
        pending = draft_settings.get("pending_reboot", [])
        if pending:
            self.pending_reboot_label.set_text(
                self.tr(
                    "Restart required for: {pending}",
                    pending=", ".join(str(item).replace("_", " ") for item in pending),
                )
            )
        else:
            self.pending_reboot_label.set_text(self.tr("The current draft does not require a reboot."))

    def on_profile_preview_changed(self, *_args) -> None:
        self.refresh_summary()

    def on_draft_settings_changed(self, *_args) -> None:
        self.refresh_summary()

    def on_theme_preview_changed(self, *_args) -> None:
        self.preview_theme()
        self.refresh_summary()

    def on_refresh(self, _button: Gtk.Button) -> None:
        try:
            self.settings = self.client.get_settings()
            self.backend_ready = True
            self.apply_button.set_sensitive(True)
            self.reset_button.set_sensitive(True)
        except SettingsClientError as error:
            self.backend_ready = False
            self.apply_button.set_sensitive(False)
            self.reset_button.set_sensitive(False)
            self.status_label.set_text(f"{self.format_backend_guidance(error)} Review mode only until service is reachable.")
            return
        self.restore_settings()
        self.refresh_summary()
        self.status_label.set_text("Settings refreshed.")

    def on_reset_to_profile(self, _button: Gtk.Button) -> None:
        try:
            self.client.apply_preset(self._selected_value(self.profile_combo, self.profile_values))
            self.settings = self.client.commit()
        except SettingsClientError as error:
            self.status_label.set_text(self.format_backend_guidance(error))
            return
        self.restore_settings()
        self.refresh_summary()
        self.status_label.set_text("Overrides removed. The selected profile is active again.")

    def on_apply(self, _button: Gtk.Button) -> None:
        profile = self._selected_value(self.profile_combo, self.profile_values)
        values = self.collect_values()
        overrides = derive_overrides_for_profile(profile, values)
        try:
            self.client.apply_preset(profile)
            if overrides:
                self.client.set_overrides(overrides)
            self.settings = self.client.commit()
        except SettingsClientError as error:
            self.status_label.set_text(self.format_backend_guidance(error))
            return
        self.restore_settings()
        self.refresh_summary()
        if self.settings.get("pending_reboot"):
            self.status_label.set_text("Changes saved. Some protections apply after the next reboot.")
        else:
            self.status_label.set_text("Changes saved.")

    def on_diagnostics(self, _button: Gtk.Button) -> None:
        self.status_label.set_text(
            "Diagnostics: systemctl status nmos-settings.service; journalctl -u nmos-settings.service -n 50"
        )


class ControlCenterApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.nmos.ControlCenter")

    def do_activate(self) -> None:
        load_css()
        window = self.props.active_window
        if window is None:
            window = ControlCenterWindow(self)
        window.present()


def main() -> None:
    app = ControlCenterApplication()
    app.run([])


if __name__ == "__main__":
    main()
