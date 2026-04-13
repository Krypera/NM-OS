import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def string_dropdown(labels: list[str]) -> Gtk.DropDown:
    return Gtk.DropDown(model=Gtk.StringList.new(labels))

def labelled_control(title: str, description: str, control: Gtk.Widget) -> Gtk.Widget:
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

def page(title: str, subtitle: str, children: list[Gtk.Widget]) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    title_label = Gtk.Label(label=title, xalign=0)
    title_label.add_css_class("title-2")
    header.append(title_label)
    if subtitle:
        subtitle_label = Gtk.Label(label=subtitle, xalign=0)
        subtitle_label.set_wrap(True)
        subtitle_label.add_css_class("dim-label")
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
