from __future__ import annotations

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk
from nmos_common.i18n import (
    LANGUAGE_OPTIONS,
    display_language_name,
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
from nmos_common.settings_client import SettingsClient
from nmos_common.system_settings import (
    ACCENT_LABELS,
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
VAULT_AUTO_LOCK_OPTIONS = (
    ("0", "Manual lock"),
    ("5", "5 minutes"),
    ("15", "15 minutes"),
    ("30", "30 minutes"),
    ("60", "1 hour"),
)


def _string_dropdown(labels: list[str]) -> Gtk.DropDown:
    return Gtk.DropDown(model=Gtk.StringList.new(labels))


def _labelled_control(title: str, description: str, control: Gtk.Widget) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    title_label = Gtk.Label(label=title, xalign=0)
    title_label.add_css_class("title-4")
    description_label = Gtk.Label(label=description, xalign=0)
    description_label.set_wrap(True)
    description_label.add_css_class("dim-label")
    box.append(title_label)
    box.append(description_label)
    box.append(control)
    return box


def _page(title: str, subtitle: str, children: list[Gtk.Widget]) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    title_label = Gtk.Label(label=title, xalign=0)
    title_label.add_css_class("title-2")
    subtitle_label = Gtk.Label(label=subtitle, xalign=0)
    subtitle_label.set_wrap(True)
    subtitle_label.add_css_class("dim-label")
    header.append(title_label)
    header.append(subtitle_label)
    box.append(header)
    for child in children:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_top(14)
        inner.set_margin_bottom(14)
        inner.set_margin_start(14)
        inner.set_margin_end(14)
        inner.append(child)
        frame.set_child(inner)
        box.append(frame)
    return box


class ControlCenterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NM-OS Control Center")
        self.set_default_size(1080, 720)
        self.client = SettingsClient()
        self.settings = self.client.get_settings()
        self.profile_values = list(PROFILE_METADATA)
        self.language_values = [locale for locale, _label in LANGUAGE_OPTIONS]
        self.ui_locale = resolve_supported_locale(self.settings.get("locale", "en_US.UTF-8"))
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.root.set_margin_top(24)
        self.root.set_margin_bottom(24)
        self.root.set_margin_start(24)
        self.root.set_margin_end(24)
        self.build_ui()
        self.restore_settings()
        self.refresh_summary()
        self.set_content(self.root)

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
            label="Tune privacy, appearance, and recovery behavior without leaving the desktop.",
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

        self.profile_combo = _string_dropdown([PROFILE_METADATA[key]["label"] for key in self.profile_values])
        self.profile_combo.connect("notify::selected", self.on_profile_preview_changed)
        self.profile_summary = Gtk.Label(xalign=0)
        self.profile_summary.set_wrap(True)
        self.profile_guidance = Gtk.Label(xalign=0)
        self.profile_guidance.set_wrap(True)
        self.profile_guidance.add_css_class("dim-label")
        self.profile_tradeoff = Gtk.Label(xalign=0)
        self.profile_tradeoff.set_wrap(True)
        self.profile_tradeoff.add_css_class("dim-label")
        self.profile_details = Gtk.Label(xalign=0)
        self.profile_details.set_wrap(True)
        self.profile_meter_label = Gtk.Label(xalign=0)
        self.profile_meter_label.set_wrap(True)
        self.profile_meter_label.add_css_class("dim-label")
        self.profile_shift_label = Gtk.Label(xalign=0)
        self.profile_shift_label.set_wrap(True)
        self.profile_shift_label.add_css_class("dim-label")
        self.change_timing_label = Gtk.Label(xalign=0)
        self.change_timing_label.set_wrap(True)
        self.change_detail_label = Gtk.Label(xalign=0)
        self.change_detail_label.set_wrap(True)
        self.change_detail_label.add_css_class("dim-label")
        self.pending_reboot_label = Gtk.Label(xalign=0)
        self.pending_reboot_label.set_wrap(True)

        self.language_combo = _string_dropdown([display_language_name(locale) for locale in self.language_values])
        self.language_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.keyboard_combo = _string_dropdown(list(KEYBOARD_OPTIONS))
        self.keyboard_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.network_combo = _string_dropdown([label for _value, label in NETWORK_OPTIONS])
        self.network_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.brave_switch = Gtk.Switch()
        self.brave_switch.connect("notify::active", self.on_draft_settings_changed)
        self.sandbox_combo = _string_dropdown([label for _value, label in SANDBOX_OPTIONS])
        self.sandbox_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.device_policy_combo = _string_dropdown([label for _value, label in DEVICE_POLICY_OPTIONS])
        self.device_policy_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.logging_combo = _string_dropdown([label for _value, label in LOGGING_OPTIONS])
        self.logging_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.theme_profile_combo = _string_dropdown([label for _value, label in THEME_PROFILE_OPTIONS])
        self.accent_combo = _string_dropdown([label for _value, label in ACCENT_OPTIONS])
        self.density_combo = _string_dropdown([label for _value, label in DENSITY_OPTIONS])
        self.motion_combo = _string_dropdown([label for _value, label in MOTION_OPTIONS])
        self.vault_auto_lock_combo = _string_dropdown([label for _value, label in VAULT_AUTO_LOCK_OPTIONS])
        self.vault_auto_lock_combo.connect("notify::selected", self.on_draft_settings_changed)
        self.vault_unlock_on_login = Gtk.Switch()
        self.vault_unlock_on_login.connect("notify::active", self.on_draft_settings_changed)
        self.privacy_explanation = Gtk.Label(xalign=0)
        self.privacy_explanation.set_wrap(True)
        self.privacy_explanation.add_css_class("dim-label")
        self.apps_explanation = Gtk.Label(xalign=0)
        self.apps_explanation.set_wrap(True)
        self.apps_explanation.add_css_class("dim-label")
        self.vault_explanation = Gtk.Label(xalign=0)
        self.vault_explanation.set_wrap(True)
        self.vault_explanation.add_css_class("dim-label")
        self.system_explanation = Gtk.Label(xalign=0)
        self.system_explanation.set_wrap(True)
        self.system_explanation.add_css_class("dim-label")

        for dropdown in (
            self.theme_profile_combo,
            self.accent_combo,
            self.density_combo,
            self.motion_combo,
        ):
            dropdown.connect("notify::selected", self.on_theme_preview_changed)

        self.profile_page = _page(
            "Profiles",
            "Pick a security posture, then refine it with advanced pages if you want more control.",
            [
                _labelled_control(
                    "Security profile",
                    "Balanced is recommended. Other profiles trade comfort for stronger or lighter restrictions.",
                    self.profile_combo,
                ),
                self.profile_summary,
                self.profile_guidance,
                self.profile_tradeoff,
                self.profile_meter_label,
                self.profile_shift_label,
                self.profile_details,
                self.change_timing_label,
                self.change_detail_label,
                self.pending_reboot_label,
            ],
        )

        self.privacy_page = _page(
            "Privacy & Network",
            "Choose how networking behaves and whether a privacy-focused browser should appear when available.",
            [
                _labelled_control("Network policy", "Tor-first keeps the safest baseline.", self.network_combo),
                _labelled_control(
                    "Allow Brave Browser",
                    "Brave stays hidden unless the build enables it and you allow it here.",
                    self.brave_switch,
                ),
                self.privacy_explanation,
            ],
        )

        self.apps_page = _page(
            "Apps & Permissions",
            "Flatpak plus desktop portals is the first app-boundary layer for NM-OS.",
            [
                _labelled_control(
                    "Default app isolation",
                    "Focused is the default middle ground between broad access and strict confinement.",
                    self.sandbox_combo,
                ),
                Gtk.Label(
                    label="Per-app overrides will land later. This first slice keeps the default policy readable and easy to change.",
                    xalign=0,
                ),
                self.apps_explanation,
            ],
        )

        self.vault_page = _page(
            "Vault",
            "Save your preferred encrypted vault behavior and session handling defaults.",
            [
                _labelled_control(
                    "Auto-lock",
                    "Choose how quickly the encrypted vault should relock after inactivity.",
                    self.vault_auto_lock_combo,
                ),
                _labelled_control(
                    "Unlock on login",
                    "Keep this off unless you explicitly want convenience ahead of stronger separation.",
                    self.vault_unlock_on_login,
                ),
                self.vault_explanation,
            ],
        )

        self.system_page = _page(
            "System & Recovery",
            "Control removable-media behavior, logging posture, and how quickly you can get back to a clean profile.",
            [
                _labelled_control(
                    "Device policy",
                    "Prompt is the recommended baseline for external devices and removable media.",
                    self.device_policy_combo,
                ),
                _labelled_control(
                    "Logging policy",
                    "Minimal keeps diagnostics useful without retaining more than necessary.",
                    self.logging_combo,
                ),
                self.system_explanation,
            ],
        )

        self.language_page = _page(
            "Language & Region",
            "Adjust display language and keyboard defaults for new sessions.",
            [
                _labelled_control("Language", "English remains the source language and Spanish is included today.", self.language_combo),
                _labelled_control("Keyboard", "Choose the default keyboard layout for the next login.", self.keyboard_combo),
            ],
        )

        self.appearance_page = _page(
            "Appearance",
            "NM-OS uses a retro-futuristic theme language with limited, intentional customization.",
            [
                _labelled_control("Theme profile", "Switch between the three supported NM-OS looks.", self.theme_profile_combo),
                _labelled_control("Accent", "Accents are intentionally limited to keep the system cohesive.", self.accent_combo),
                _labelled_control("Density", "Comfortable is easier to read; compact fits more information.", self.density_combo),
                _labelled_control("Motion", "Reduced motion lowers distraction while keeping the interface responsive.", self.motion_combo),
            ],
        )

        pages = [
            ("profiles", "Profiles", self.profile_page),
            ("privacy", "Privacy & Network", self.privacy_page),
            ("apps", "Apps & Permissions", self.apps_page),
            ("vault", "Vault", self.vault_page),
            ("system", "System & Recovery", self.system_page),
            ("language", "Language & Region", self.language_page),
            ("appearance", "Appearance", self.appearance_page),
        ]
        for key, title, widget in pages:
            self.stack.add_titled(widget, key, title)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.refresh_button = Gtk.Button(label="Refresh")
        self.reset_button = Gtk.Button(label="Reset To Profile")
        self.apply_button = Gtk.Button(label="Apply Changes")
        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_hexpand(True)
        self.status_label.set_wrap(True)
        self.status_label.add_css_class("dim-label")
        self.refresh_button.connect("clicked", self.on_refresh)
        self.reset_button.connect("clicked", self.on_reset_to_profile)
        self.apply_button.connect("clicked", self.on_apply)
        actions.append(self.status_label)
        actions.append(self.refresh_button)
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
        self.settings = self.client.get_settings()
        self.restore_settings()
        self.refresh_summary()
        self.status_label.set_text("Settings refreshed.")

    def on_reset_to_profile(self, _button: Gtk.Button) -> None:
        self.client.apply_preset(self._selected_value(self.profile_combo, self.profile_values))
        self.settings = self.client.commit()
        self.restore_settings()
        self.refresh_summary()
        self.status_label.set_text("Overrides removed. The selected profile is active again.")

    def on_apply(self, _button: Gtk.Button) -> None:
        profile = self._selected_value(self.profile_combo, self.profile_values)
        values = self.collect_values()
        overrides = derive_overrides_for_profile(profile, values)
        self.client.apply_preset(profile)
        if overrides:
            self.client.set_overrides(overrides)
        self.settings = self.client.commit()
        self.restore_settings()
        self.refresh_summary()
        if self.settings.get("pending_reboot"):
            self.status_label.set_text("Changes saved. Some protections apply after the next reboot.")
        else:
            self.status_label.set_text("Changes saved.")


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
