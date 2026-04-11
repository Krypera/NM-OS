from __future__ import annotations

from pathlib import Path

THEME_CSS_FILE = Path("/usr/share/nmos/theme/nmos.css")


def _import_gtk():
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gdk, Gtk

    return Gdk, Gtk


def load_css(css_path: Path = THEME_CSS_FILE) -> None:
    if not css_path.exists():
        return
    gdk, gtk = _import_gtk()
    display = gdk.Display.get_default()
    if display is None:
        return
    provider = gtk.CssProvider()
    provider.load_from_path(str(css_path))
    gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def apply_window_theme(widget, settings: dict) -> None:
    for prefix in ("theme-", "accent-", "density-", "motion-"):
        for css_class in list(widget.get_css_classes()):
            if css_class.startswith(prefix):
                widget.remove_css_class(css_class)
    widget.add_css_class("nmos-root")
    widget.add_css_class(f"theme-{settings.get('ui_theme_profile', 'nmos-classic')}")
    widget.add_css_class(f"accent-{settings.get('ui_accent', 'amber')}")
    widget.add_css_class(f"density-{settings.get('ui_density', 'comfortable')}")
    widget.add_css_class(f"motion-{settings.get('ui_motion', 'full')}")
