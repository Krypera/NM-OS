from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from nmos_common.i18n import (
    display_language_name,
    display_network_policy_name,
    explain_brave_visibility,
    explain_network_policy,
    format_change_detail,
    format_posture_shift,
    posture_explanation_lines,
    posture_meter_lines,
    resolve_supported_locale,
)
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
from nmos_common.ui_theme import apply_window_theme

KEYBOARD_OPTIONS = ["us", "tr", "de", "fr"]


def _combo(values: list[str]) -> Gtk.DropDown:
    model = Gtk.StringList.new(values)
    return Gtk.DropDown(model=model)


def _page(window, page_key: str, title_text: str, subtitle_text: str, controls: list[Gtk.Widget]) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    title = Gtk.Label(label=title_text, xalign=0)
    title.add_css_class("title-3")
    subtitle = Gtk.Label(label=subtitle_text, xalign=0)
    subtitle.set_wrap(True)
    subtitle.add_css_class("dim-label")
    setattr(window, f"{page_key}_title_label", title)
    setattr(window, f"{page_key}_subtitle_label", subtitle)
    box.append(title)
    box.append(subtitle)
    for control in controls:
        box.append(control)
    return box


def _profile_page(window) -> Gtk.Widget:
    return _page(
        window,
        "profile",
        "Security profile",
        "Choose a starting point. You can still fine-tune it later from the desktop.",
        [
            window.profile_combo,
            window.profile_summary_label,
            window.profile_guidance_label,
            window.profile_tradeoff_label,
            window.profile_details_label,
        ],
    )


def _network_page(window) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.network_title_label = Gtk.Label(label="Network", xalign=0)
    window.network_title_label.add_css_class("title-3")
    window.network_subtitle_label = Gtk.Label(label="Choose how NM-OS should treat the network.", xalign=0)
    window.network_subtitle_label.set_wrap(True)
    window.network_subtitle_label.add_css_class("dim-label")
    window.network_policy_label = Gtk.Label(label="Network policy", xalign=0)
    box.append(window.network_title_label)
    box.append(window.network_subtitle_label)
    box.append(window.network_policy_label)
    box.append(window.network_policy_combo)
    box.append(window.allow_brave_browser)
    box.append(window.network_explanation_label)
    box.append(window.network_label)
    box.append(window.network_progress)
    box.append(window.network_refresh)
    return box


def _appearance_page(window) -> Gtk.Widget:
    return _page(
        window,
        "appearance",
        "Appearance",
        "Keep the visual language intentional. A few curated options go a long way.",
        [
            window.theme_profile_combo,
            window.accent_combo,
            window.density_combo,
            window.motion_combo,
        ],
    )


def _storage_page(window) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.storage_title_label = Gtk.Label(label="Encrypted Vault", xalign=0)
    window.storage_title_label.add_css_class("title-3")
    window.storage_subtitle_label = Gtk.Label(
        label="Create or unlock an encrypted vault for sensitive files.",
        xalign=0,
    )
    window.storage_subtitle_label.set_wrap(True)
    window.storage_subtitle_label.add_css_class("dim-label")
    box.append(window.storage_title_label)
    box.append(window.storage_subtitle_label)
    box.append(window.persistence_label)
    box.append(window.persistence_password)
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    actions.append(window.persistence_create)
    actions.append(window.persistence_unlock)
    actions.append(window.persistence_lock)
    actions.append(window.persistence_repair)
    box.append(actions)
    return box


def _summary_page(window) -> Gtk.Widget:
    return _page(
        window,
        "summary",
        "Review",
        "A few changes can apply right away. Network and deeper security policy changes may wait until reboot.",
        [
            window.summary_label,
            window.summary_meter_label,
            window.summary_shift_label,
            window.summary_posture_label,
            window.summary_timing_label,
            window.summary_change_detail_label,
            window.summary_reboot_label,
        ],
    )


def build_ui(window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    root.set_margin_top(24)
    root.set_margin_bottom(24)
    root.set_margin_start(24)
    root.set_margin_end(24)
    window.root_container = root

    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    window.header_title_label = Gtk.Label(label="NM-OS Setup")
    window.header_title_label.add_css_class("title-1")
    window.header_title_label.set_xalign(0)
    window.header_subtitle_label = Gtk.Label(xalign=0)
    window.header_subtitle_label.set_wrap(True)
    window.header_subtitle_label.add_css_class("dim-label")
    header.append(window.header_title_label)
    header.append(window.header_subtitle_label)
    root.append(header)

    window.session_status = Gtk.Label(xalign=0)
    window.session_status.set_wrap(True)
    window.session_status.add_css_class("caption")
    root.append(window.session_status)

    window.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
    window.stack.set_vexpand(True)

    window.language_combo = _combo([display_language_name(locale) for locale in window.language_values])
    window.keyboard_combo = _combo(KEYBOARD_OPTIONS)
    window.profile_combo = _combo([PROFILE_METADATA[profile]["label"] for profile in window.profile_values])
    window.profile_combo.connect("notify::selected", window.on_profile_changed)
    window.profile_summary_label = Gtk.Label(xalign=0)
    window.profile_summary_label.set_wrap(True)
    window.profile_summary_label.add_css_class("dim-label")
    window.profile_guidance_label = Gtk.Label(xalign=0)
    window.profile_guidance_label.set_wrap(True)
    window.profile_guidance_label.add_css_class("dim-label")
    window.profile_tradeoff_label = Gtk.Label(xalign=0)
    window.profile_tradeoff_label.set_wrap(True)
    window.profile_tradeoff_label.add_css_class("dim-label")
    window.profile_details_label = Gtk.Label(xalign=0)
    window.profile_details_label.set_wrap(True)
    window.network_policy_combo = _combo([display_network_policy_name(policy) for policy in window.network_policy_values])
    window.network_policy_combo.connect("notify::selected", window.on_network_policy_changed)
    window.allow_brave_browser = Gtk.CheckButton()
    window.allow_brave_browser.connect("toggled", window.on_allow_brave_browser_toggled)
    window.network_explanation_label = Gtk.Label(xalign=0)
    window.network_explanation_label.set_wrap(True)
    window.network_explanation_label.add_css_class("dim-label")
    window.theme_profile_combo = _combo([THEME_PROFILE_LABELS[value] for value in window.theme_profile_values])
    window.theme_profile_combo.connect("notify::selected", window.on_theme_preview_changed)
    window.accent_combo = _combo([ACCENT_LABELS[value] for value in window.accent_values])
    window.accent_combo.connect("notify::selected", window.on_theme_preview_changed)
    window.density_combo = _combo([DENSITY_LABELS[value] for value in window.density_values])
    window.density_combo.connect("notify::selected", window.on_theme_preview_changed)
    window.motion_combo = _combo([MOTION_LABELS[value] for value in window.motion_values])
    window.motion_combo.connect("notify::selected", window.on_theme_preview_changed)
    window.network_progress = Gtk.ProgressBar()
    window.network_label = Gtk.Label(xalign=0)
    window.network_refresh = Gtk.Button()
    window.network_refresh.connect("clicked", window.on_refresh_network)

    window.persistence_label = Gtk.Label(xalign=0)
    window.persistence_label.set_wrap(True)
    window.persistence_password = Gtk.PasswordEntry()
    window.persistence_create = Gtk.Button()
    window.persistence_unlock = Gtk.Button()
    window.persistence_lock = Gtk.Button()
    window.persistence_repair = Gtk.Button()
    window.persistence_create.connect("clicked", window.on_create_persistence)
    window.persistence_unlock.connect("clicked", window.on_unlock_persistence)
    window.persistence_lock.connect("clicked", window.on_lock_persistence)
    window.persistence_repair.connect("clicked", window.on_repair_persistence)

    window.summary_label = Gtk.Label(xalign=0)
    window.summary_label.set_wrap(True)
    window.summary_meter_label = Gtk.Label(xalign=0)
    window.summary_meter_label.set_wrap(True)
    window.summary_meter_label.add_css_class("dim-label")
    window.summary_shift_label = Gtk.Label(xalign=0)
    window.summary_shift_label.set_wrap(True)
    window.summary_shift_label.add_css_class("dim-label")
    window.summary_posture_label = Gtk.Label(xalign=0)
    window.summary_posture_label.set_wrap(True)
    window.summary_timing_label = Gtk.Label(xalign=0)
    window.summary_timing_label.set_wrap(True)
    window.summary_change_detail_label = Gtk.Label(xalign=0)
    window.summary_change_detail_label.set_wrap(True)
    window.summary_change_detail_label.add_css_class("dim-label")
    window.summary_reboot_label = Gtk.Label(xalign=0)
    window.summary_reboot_label.set_wrap(True)
    window.summary_reboot_label.add_css_class("dim-label")

    window.page_widgets = {
        "language": _page(window, "language", "Language", "Choose the interface language.", [window.language_combo]),
        "keyboard": _page(window, "keyboard", "Keyboard", "Choose the keyboard layout.", [window.keyboard_combo]),
        "profile": _profile_page(window),
        "network": _network_page(window),
        "appearance": _appearance_page(window),
        "storage": _storage_page(window),
        "summary": _summary_page(window),
    }

    for index, key in enumerate(window.page_order):
        self_page = Gtk.Frame()
        self_page.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_top(18)
        inner.set_margin_bottom(18)
        inner.set_margin_start(18)
        inner.set_margin_end(18)
        inner.append(window.page_widgets[key])
        self_page.set_child(inner)
        window.stack.add_titled(self_page, f"page-{index}", f"Page {index + 1}")

    root.append(window.stack)

    nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    window.back_button = Gtk.Button()
    window.next_button = Gtk.Button()
    window.finish_button = Gtk.Button()
    window.finish_button.add_css_class("suggested-action")
    window.back_button.connect("clicked", window.on_back)
    window.next_button.connect("clicked", window.on_next)
    window.finish_button.connect("clicked", window.on_finish)
    nav.append(window.back_button)
    nav.append(window.next_button)
    nav.append(window.finish_button)
    root.append(nav)

    window.set_content(root)


def resolve_page_order(_window) -> list[str]:
    return ["language", "keyboard", "profile", "network", "appearance", "storage", "summary"]


def current_page_key(window) -> str:
    return window.page_order[window.page_index]


def _set_dropdown_values(dropdown: Gtk.DropDown, values: list[str], selected_index: int) -> None:
    dropdown.set_model(Gtk.StringList.new(values))
    dropdown.set_selected(selected_index)


def current_language_code(window) -> str:
    selected = window.language_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.language_values):
        window.language_combo.set_selected(0)
        return window.language_values[0]
    return window.language_values[selected]


def current_language_name(window) -> str:
    return display_language_name(current_language_code(window))


def current_profile(window) -> str:
    selected = window.profile_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.profile_values):
        window.profile_combo.set_selected(0)
        return window.profile_values[0]
    return window.profile_values[selected]


def current_profile_name(window) -> str:
    return window.tr(PROFILE_METADATA[current_profile(window)]["label"])


def current_profile_summary(window) -> str:
    return window.tr(PROFILE_METADATA[current_profile(window)]["summary"])


def current_network_policy(window) -> str:
    selected = window.network_policy_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.network_policy_values):
        window.network_policy_combo.set_selected(0)
        return window.network_policy_values[0]
    return window.network_policy_values[selected]


def current_network_policy_name(window) -> str:
    return display_network_policy_name(current_network_policy(window), locale=window.ui_locale)


def current_posture_preview(window) -> dict:
    return describe_posture_preview(current_profile(window), collect_state(window))


def current_theme_profile(window) -> str:
    selected = window.theme_profile_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.theme_profile_values):
        window.theme_profile_combo.set_selected(0)
        return window.theme_profile_values[0]
    return window.theme_profile_values[selected]


def current_theme_profile_name(window) -> str:
    return window.tr(THEME_PROFILE_LABELS[current_theme_profile(window)])


def current_accent(window) -> str:
    selected = window.accent_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.accent_values):
        window.accent_combo.set_selected(0)
        return window.accent_values[0]
    return window.accent_values[selected]


def current_accent_name(window) -> str:
    return window.tr(ACCENT_LABELS[current_accent(window)])


def current_density(window) -> str:
    selected = window.density_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.density_values):
        window.density_combo.set_selected(0)
        return window.density_values[0]
    return window.density_values[selected]


def current_density_name(window) -> str:
    return window.tr(DENSITY_LABELS[current_density(window)])


def current_motion(window) -> str:
    selected = window.motion_combo.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= len(window.motion_values):
        window.motion_combo.set_selected(0)
        return window.motion_values[0]
    return window.motion_values[selected]


def current_motion_name(window) -> str:
    return window.tr(MOTION_LABELS[current_motion(window)])


def apply_translations(window) -> None:
    language_index = window.language_values.index(current_language_code(window))
    profile_index = window.profile_values.index(current_profile(window))
    network_policy_index = window.network_policy_values.index(current_network_policy(window))
    theme_profile_index = window.theme_profile_values.index(current_theme_profile(window))
    accent_index = window.accent_values.index(current_accent(window))
    density_index = window.density_values.index(current_density(window))
    motion_index = window.motion_values.index(current_motion(window))
    _set_dropdown_values(window.language_combo, [display_language_name(locale) for locale in window.language_values], language_index)
    _set_dropdown_values(
        window.profile_combo,
        [window.tr(PROFILE_METADATA[profile]["label"]) for profile in window.profile_values],
        profile_index,
    )
    _set_dropdown_values(
        window.network_policy_combo,
        [display_network_policy_name(policy, locale=window.ui_locale) for policy in window.network_policy_values],
        network_policy_index,
    )
    _set_dropdown_values(
        window.theme_profile_combo,
        [window.tr(THEME_PROFILE_LABELS[value]) for value in window.theme_profile_values],
        theme_profile_index,
    )
    _set_dropdown_values(
        window.accent_combo,
        [window.tr(ACCENT_LABELS[value]) for value in window.accent_values],
        accent_index,
    )
    _set_dropdown_values(
        window.density_combo,
        [window.tr(DENSITY_LABELS[value]) for value in window.density_values],
        density_index,
    )
    _set_dropdown_values(
        window.motion_combo,
        [window.tr(MOTION_LABELS[value]) for value in window.motion_values],
        motion_index,
    )

    window.set_title(window.tr("NM-OS Setup"))
    window.header_subtitle_label.set_text(window.tr("Review your privacy and desktop settings before login."))
    window.language_title_label.set_text(window.tr("Language"))
    window.language_subtitle_label.set_text(window.tr("Choose the interface language."))
    window.keyboard_title_label.set_text(window.tr("Keyboard"))
    window.keyboard_subtitle_label.set_text(window.tr("Choose the keyboard layout."))
    window.profile_title_label.set_text(window.tr("Security profile"))
    window.profile_subtitle_label.set_text(
        window.tr("Choose a starting point. You can still fine-tune it later from the desktop.")
    )
    window.network_title_label.set_text(window.tr("Network"))
    window.network_subtitle_label.set_text(window.tr("Choose how NM-OS should treat the network."))
    window.network_policy_label.set_text(window.tr("Network policy"))
    window.allow_brave_browser.set_label(window.tr("Allow Brave Browser when installed"))
    window.network_refresh.set_label(window.tr("Refresh network status"))
    window.appearance_title_label.set_text(window.tr("Appearance"))
    window.appearance_subtitle_label.set_text(
        window.tr("Keep the visual language intentional. A few curated options go a long way.")
    )
    window.storage_title_label.set_text(window.tr("Encrypted Vault"))
    window.storage_subtitle_label.set_text(window.tr("Create or unlock an encrypted vault for sensitive files."))
    window.summary_title_label.set_text(window.tr("Review"))
    window.summary_subtitle_label.set_text(
        window.tr("A few changes can apply right away. Network and deeper security policy changes may wait until reboot.")
    )
    window.persistence_create.set_label(window.tr("Create"))
    window.persistence_unlock.set_label(window.tr("Unlock"))
    window.persistence_lock.set_label(window.tr("Lock"))
    window.persistence_repair.set_label(window.tr("Repair"))
    window.back_button.set_label(window.tr("Back"))
    window.next_button.set_label(window.tr("Next"))
    window.finish_button.set_label(window.tr("Apply settings"))
    refresh_profile_explanation(window)
    refresh_summary(window)
    if window.persistence_init_error:
        window.persistence_label.set_text(
            window.tr(
                "Encrypted vault backend unavailable: {error}",
                error=window.translate_message(window.persistence_init_error),
            )
        )
    elif window.persistence_state:
        window.persistence_label.set_text(window.render_persistence_state(window.persistence_state))


def apply_settings_ui_policy(window) -> None:
    offline = current_network_policy(window) == "offline"
    if offline:
        window.allow_brave_browser.set_active(False)
    window.allow_brave_browser.set_sensitive(not offline)
    preview_theme(window)


def _select_string(dropdown: Gtk.DropDown, values: list[str], value: str) -> None:
    try:
        dropdown.set_selected(values.index(value))
    except ValueError:
        dropdown.set_selected(0)


def _select_language(window, locale: str) -> None:
    resolved = resolve_supported_locale(locale)
    _select_string(window.language_combo, window.language_values, resolved)


def _select_network_policy(window, policy: str) -> None:
    normalized = str(policy or "tor").strip().lower()
    _select_string(window.network_policy_combo, window.network_policy_values, normalized)


def _select_profile(window, profile: str) -> None:
    normalized = str(profile or "balanced").strip().lower()
    _select_string(window.profile_combo, window.profile_values, normalized)


def current_string(dropdown: Gtk.DropDown, values: list[str] | None = None) -> str:
    model = dropdown.get_model()
    selected = dropdown.get_selected()
    if selected == Gtk.INVALID_LIST_POSITION or selected >= model.get_n_items():
        if model.get_n_items() == 0:
            return ""
        dropdown.set_selected(0)
        selected = 0
    if values is not None and selected < len(values):
        return values[selected]
    return model.get_string(selected)


def restore_state(window) -> None:
    locale = window.state.get("locale", "en_US.UTF-8")
    keyboard = window.state.get("keyboard", "us")
    profile = window.state.get("active_profile", "balanced")
    network_policy = window.state.get("network_policy", "tor")
    allow_brave = bool(window.state.get("allow_brave_browser", False))
    _select_language(window, locale)
    _select_string(window.keyboard_combo, KEYBOARD_OPTIONS, keyboard)
    _select_profile(window, profile)
    _select_network_policy(window, network_policy)
    _select_string(window.theme_profile_combo, window.theme_profile_values, str(window.state.get("ui_theme_profile", "nmos-classic")))
    _select_string(window.accent_combo, window.accent_values, str(window.state.get("ui_accent", "amber")))
    _select_string(window.density_combo, window.density_values, str(window.state.get("ui_density", "comfortable")))
    _select_string(window.motion_combo, window.motion_values, str(window.state.get("ui_motion", "full")))
    window.allow_brave_browser.set_active(allow_brave)
    refresh_profile_explanation(window)
    apply_settings_ui_policy(window)


def preview_theme(window) -> None:
    apply_window_theme(
        window.root_container,
        {
            "ui_theme_profile": current_theme_profile(window),
            "ui_accent": current_accent(window),
            "ui_density": current_density(window),
            "ui_motion": current_motion(window),
        },
    )


def refresh_profile_explanation(window) -> None:
    posture = current_posture_preview(window)
    detail_lines = posture_explanation_lines(window.ui_locale, posture)
    window.profile_summary_label.set_text(window.tr(posture["summary"]))
    window.profile_guidance_label.set_text(window.tr(posture["ideal_for"]))
    window.profile_tradeoff_label.set_text(window.tr(posture["tradeoff"]))
    window.profile_details_label.set_text("\n".join(f"- {line}" for line in detail_lines))
    window.network_explanation_label.set_text(
        "\n".join(
            [
                explain_network_policy(window.ui_locale, current_network_policy(window)),
                explain_brave_visibility(
                    window.ui_locale,
                    window.allow_brave_browser.get_active(),
                    current_network_policy(window),
                ),
            ]
        )
    )


def refresh_summary(window) -> None:
    draft_state = collect_state(window)
    posture = describe_posture_preview(draft_state["active_profile"], draft_state)
    effective_payload = {
        "active_profile": draft_state["active_profile"],
        "overrides": derive_overrides_for_profile(draft_state["active_profile"], draft_state),
    }
    change_details = describe_effective_change_details(effective_payload)
    immediate_details = change_details["immediate"]
    reboot_details = change_details["reboot"]
    immediate_labels = [window.tr(setting_display_name(str(item["key"]))) for item in immediate_details]
    reboot_labels = [window.tr(setting_display_name(str(item["key"]))) for item in reboot_details]
    draft_settings = normalize_system_settings(
        {
            "active_profile": draft_state["active_profile"],
            "overrides": derive_overrides_for_profile(draft_state["active_profile"], draft_state),
        }
    )
    summary_lines = [
        window.tr("Profile: {profile}", profile=current_profile_name(window)),
        window.tr("Language: {language}", language=current_language_name(window)),
        window.tr("Keyboard: {keyboard}", keyboard=current_string(window.keyboard_combo, KEYBOARD_OPTIONS)),
        window.tr("Network: {network}", network=current_network_policy_name(window)),
        window.tr("Theme: {theme}", theme=current_theme_profile_name(window)),
        window.tr("Accent: {accent}", accent=current_accent_name(window)),
    ]
    if window.allow_brave_browser.get_active():
        summary_lines.append(window.tr("Brave visibility: allowed when installed"))
    else:
        summary_lines.append(window.tr("Brave visibility: hidden"))
    window.summary_label.set_text("\n".join(summary_lines))
    window.summary_meter_label.set_text("\n".join(posture_meter_lines(window.ui_locale, posture)))
    baseline_scores = compute_posture_scores(window.state)
    shift = compute_posture_score_shift(baseline_scores, posture.get("scores", {}))
    window.summary_shift_label.set_text(format_posture_shift(window.ui_locale, shift))
    window.summary_posture_label.set_text(
        "\n".join(f"- {line}" for line in posture_explanation_lines(window.ui_locale, posture))
    )
    if immediate_labels or reboot_labels:
        window.summary_timing_label.set_text(
            "\n".join(
                [
                    window.tr(
                        "Applies now: {changes}",
                        changes=", ".join(immediate_labels) if immediate_labels else window.tr("None"),
                    ),
                    window.tr(
                        "Applies after reboot: {changes}",
                        changes=", ".join(reboot_labels) if reboot_labels else window.tr("None"),
                    ),
                ]
            )
        )
        detail_lines: list[str] = []
        if immediate_details:
            detail_lines.append(window.tr("Change details (now):"))
            detail_lines.extend(
                f"- {format_change_detail(window.ui_locale, window.tr(setting_display_name(str(item['key']))), str(item['key']), item.get('from'), item.get('to'))}"
                for item in immediate_details
            )
        if reboot_details:
            detail_lines.append(window.tr("Change details (after reboot):"))
            detail_lines.extend(
                f"- {format_change_detail(window.ui_locale, window.tr(setting_display_name(str(item['key']))), str(item['key']), item.get('from'), item.get('to'))}"
                for item in reboot_details
            )
        window.summary_change_detail_label.set_text("\n".join(detail_lines))
    else:
        window.summary_timing_label.set_text(window.tr("No changed settings in the current draft."))
        window.summary_change_detail_label.set_text("")
    if draft_settings.get("pending_reboot"):
        pending = ", ".join(str(item).replace("_", " ") for item in draft_settings["pending_reboot"])
        window.summary_reboot_label.set_text(window.tr("Restart required for: {pending}", pending=pending))
    else:
        window.summary_reboot_label.set_text(window.tr("The current draft does not require a reboot."))


def set_status(window, text: str, *, source: str = "event", force: bool = True) -> None:
    if not force and source == "network" and window.status_source not in {"", "network"}:
        return
    window.status_source = source
    window.session_status.set_text(text)


def collect_state(window) -> dict:
    return {
        "locale": current_language_code(window),
        "keyboard": current_string(window.keyboard_combo, KEYBOARD_OPTIONS),
        "active_profile": current_profile(window),
        "network_policy": current_network_policy(window),
        "allow_brave_browser": window.allow_brave_browser.get_active(),
        "ui_theme_profile": current_theme_profile(window),
        "ui_accent": current_accent(window),
        "ui_density": current_density(window),
        "ui_motion": current_motion(window),
    }


def can_finish(window) -> bool:
    if window.persistence_state.get("busy") or window.persistence_action_in_progress or window.persistence_refresh_in_progress:
        return False
    return True


def update_navigation(window) -> None:
    if current_page_key(window) == "summary":
        refresh_summary(window)
    window.back_button.set_sensitive(window.page_index > 0)
    window.next_button.set_visible(window.page_index < len(window.page_order) - 1)
    window.next_button.set_sensitive(True)
    window.finish_button.set_visible(window.page_index == len(window.page_order) - 1)
    window.finish_button.set_sensitive(can_finish(window))
