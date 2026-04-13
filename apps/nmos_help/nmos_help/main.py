import os
import re

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk


def md_to_pango(text: str) -> str:
    # Extremely basic Markdown-to-Pango parser for help articles
    text = GLib.markup_escape_text(text)
    # Headers
    text = re.sub(r"^###\s+(.*)", r'<span size="large" weight="bold">\1</span>\n', text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.*)", r'<span size="x-large" weight="bold">\1</span>\n', text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.*)", r'<span size="xx-large" weight="bold">\1</span>\n', text, flags=re.MULTILINE)
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Fix double escaping for newlines
    text = text.replace("\n", "\n")
    return text


class HelpWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="System Help")
        self.set_default_size(860, 600)

        self.guides_dir = "/usr/share/doc/nmos/user-guides"
        if not os.path.exists(self.guides_dir):
            # Development fallback
            self.guides_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../docs/user-guides"))

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.sidebar = Gtk.StackSidebar()
        self.sidebar.set_stack(self.stack)
        self.sidebar.set_vexpand(True)
        self.sidebar.set_size_request(240, -1)

        split.append(self.sidebar)
        split.append(self.stack)

        self.load_guides()
        self.set_content(split)

    def load_guides(self) -> None:
        files = [
            ("getting-started.md", "Getting Started"),
            ("files-and-folders.md", "Files & Folders"),
            ("internet-and-email.md", "Internet & Email"),
            ("printing.md", "Printing"),
            ("software-installation.md", "Installing Software"),
        ]

        for fname, title in files:
            path = os.path.join(self.guides_dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                content = f"Could not load documentation from {path}."

            markup = md_to_pango(content)

            label = Gtk.Label(xalign=0, yalign=0)
            label.set_wrap(True)
            label.set_markup(markup)
            label.set_margin_top(24)
            label.set_margin_bottom(24)
            label.set_margin_start(24)
            label.set_margin_end(24)

            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_child(label)

            self.stack.add_titled(scroll, fname, title)


class HelpApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.nmos.Help")

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = HelpWindow(self)
        window.present()


def main() -> None:
    app = HelpApplication()
    app.run([])


if __name__ == "__main__":
    main()
