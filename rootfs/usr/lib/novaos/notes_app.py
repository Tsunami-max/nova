#!/usr/bin/env python3
"""Nova Notes - a simple notes app. Notes are plain Markdown files in ~/Documents/Notes."""
import os
import re
import sys
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

NOTES_DIR = os.path.join(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
                         or os.path.expanduser("~/Documents"), "Notes")

CSS = b"""
.notes-list row { padding: 10px 12px; border-radius: 8px; margin: 2px 6px; }
.notes-list row:selected { background-color: alpha(@theme_selected_bg_color, 0.25); color: @theme_fg_color; }
.notes-title { font-weight: 700; }
.notes-snippet { opacity: 0.6; font-size: 9pt; }
.notes-editor { font-family: "Inter"; font-size: 12pt; padding: 18px 24px; }
.notes-empty { opacity: 0.55; font-size: 13pt; }
"""


def first_line(text):
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:80]
    return "New note"


class Note:
    def __init__(self, path):
        self.path = path
        try:
            with open(path) as f:
                self.text = f.read()
        except OSError:
            self.text = ""
        self.mtime = os.path.getmtime(path) if os.path.exists(path) else time.time()


class NotesWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Notes")
        self.set_default_size(920, 600)
        self.set_icon_name("novaos-notes")
        os.makedirs(NOTES_DIR, exist_ok=True)
        self.current = None
        self.save_id = 0
        self.loading = False

        hb = Gtk.HeaderBar(show_close_button=True, title="Notes")
        new_b = Gtk.Button.new_from_icon_name("document-new-symbolic", Gtk.IconSize.BUTTON)
        new_b.set_tooltip_text("New note (Ctrl+N)")
        new_b.connect("clicked", lambda _b: self.new_note())
        del_b = Gtk.Button.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        del_b.set_tooltip_text("Delete note")
        del_b.connect("clicked", lambda _b: self.delete_note())
        hb.pack_start(new_b)
        hb.pack_end(del_b)
        self.set_titlebar(hb)

        paned = Gtk.Paned()
        self.add(paned)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_size_request(260, -1)
        self.search = Gtk.SearchEntry(placeholder_text="Search notes")
        self.search.set_margin_start(8)
        self.search.set_margin_end(8)
        self.search.set_margin_top(8)
        self.search.connect("search-changed", lambda _e: self.listbox.invalidate_filter())
        left.pack_start(self.search, False, False, 0)
        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("notes-list")
        self.listbox.set_filter_func(self.filter_row)
        self.listbox.connect("row-selected", self.on_select)
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sc.add(self.listbox)
        left.pack_start(sc, True, True, 0)
        paned.pack1(left, False, False)

        self.right = Gtk.Stack()
        self.view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.view.get_style_context().add_class("notes-editor")
        self.buffer = self.view.get_buffer()
        self.buffer.connect("changed", self.on_changed)
        esc = Gtk.ScrolledWindow()
        esc.add(self.view)
        empty = Gtk.Label(label="No note selected.\nPress Ctrl+N to create one.")
        empty.set_justify(Gtk.Justification.CENTER)
        empty.get_style_context().add_class("notes-empty")
        self.right.add_named(empty, "empty")
        self.right.add_named(esc, "editor")
        paned.pack2(self.right, True, False)

        accel = Gtk.AccelGroup()
        accel.connect(Gdk_keyval("n"), CTRL, 0, lambda *a: self.new_note() or True)
        accel.connect(Gdk_keyval("s"), CTRL, 0, lambda *a: self.flush() or True)
        accel.connect(Gdk_keyval("f"), CTRL, 0, lambda *a: self.search.grab_focus() or True)
        self.add_accel_group(accel)
        self.connect("delete-event", lambda *_a: self.flush() and False)

        self.reload()

    # ------------------------------------------------------------------
    def reload(self, select_path=None):
        for r in self.listbox.get_children():
            self.listbox.remove(r)
        notes = [Note(os.path.join(NOTES_DIR, f)) for f in os.listdir(NOTES_DIR) if f.endswith(".md")]
        notes.sort(key=lambda n: n.mtime, reverse=True)
        for n in notes:
            self.listbox.add(self.make_row(n))
        self.listbox.show_all()
        target = None
        for r in self.listbox.get_children():
            if select_path is None or r.note.path == select_path:
                target = r
                break
        if target:
            self.listbox.select_row(target)
        else:
            self.right.set_visible_child_name("empty")

    def make_row(self, note):
        r = Gtk.ListBoxRow()
        r.note = note
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        t = Gtk.Label(label=first_line(note.text), xalign=0, ellipsize=Pango.EllipsizeMode.END)
        t.get_style_context().add_class("notes-title")
        body = " ".join(note.text.split()[len(first_line(note.text).split()):])[:90]
        s = Gtk.Label(label=time.strftime("%d %b %H:%M", time.localtime(note.mtime)) + "  " + body,
                      xalign=0, ellipsize=Pango.EllipsizeMode.END)
        s.get_style_context().add_class("notes-snippet")
        v.pack_start(t, False, False, 0)
        v.pack_start(s, False, False, 0)
        r.add(v)
        r.title_label = t
        return r

    def filter_row(self, r):
        q = self.search.get_text().lower()
        return not q or q in r.note.text.lower()

    def on_select(self, _lb, r):
        self.flush()
        if not r:
            return
        self.current = r
        self.loading = True
        self.buffer.set_text(r.note.text)
        self.loading = False
        self.right.set_visible_child_name("editor")
        self.view.grab_focus()

    def on_changed(self, _buf):
        if self.loading or not self.current:
            return
        start, end = self.buffer.get_bounds()
        self.current.note.text = self.buffer.get_text(start, end, True)
        self.current.title_label.set_text(first_line(self.current.note.text))
        if self.save_id:
            GLib.source_remove(self.save_id)
        self.save_id = GLib.timeout_add(600, self.flush)

    def flush(self):
        if self.save_id:
            GLib.source_remove(self.save_id)
            self.save_id = 0
        if self.current:
            n = self.current.note
            tmp = n.path + ".tmp"
            with open(tmp, "w") as f:
                f.write(n.text)
            os.replace(tmp, n.path)
        return False

    def new_note(self):
        self.flush()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(NOTES_DIR, f"note-{stamp}.md")
        i = 1
        while os.path.exists(path):
            path = os.path.join(NOTES_DIR, f"note-{stamp}-{i}.md")
            i += 1
        with open(path, "w") as f:
            f.write("New note\n\n")
        self.search.set_text("")
        self.reload(path)
        self.buffer.select_range(self.buffer.get_start_iter(),
                                 self.buffer.get_iter_at_line_offset(0, 8))

    def delete_note(self):
        if not self.current:
            return
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.OK_CANCEL,
                              text="Move “%s” to the Trash?" % first_line(self.current.note.text))
        resp = d.run()
        d.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        path = self.current.note.path
        self.current = None
        try:
            from gi.repository import Gio
            Gio.File.new_for_path(path).trash(None)
        except Exception:  # trash unavailable: delete permanently
            os.remove(path)
        self.reload()


from gi.repository import Gdk  # noqa: E402
CTRL = Gdk.ModifierType.CONTROL_MASK


def Gdk_keyval(ch):
    return Gdk.keyval_from_name(ch)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="os.nova.Notes")

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            win = NotesWindow(self)
        win.show_all()
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
