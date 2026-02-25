"""
popups.py
---------
All Kivy popup/dialog classes:
  InfoPopup         — simple message + OK button
  MetadataPopup     — scrollable metadata report with copy buttons
  FilePopup         — file chooser (desktop)
  ExtractedTextPopup — scrollable text viewer with Copy All
  PDFPreviewPopup   — re-exported from preview module
"""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp

from .preview import PDFPreviewPopup  # re-export
from core.toast import core


# ── InfoPopup ─────────────────────────────────────────────────────────────────

class InfoPopup(Popup):
    message = StringProperty("")


# ── MetadataPopup ─────────────────────────────────────────────────────────────

class MetadataPopup(Popup):
    """Dynamic metadata report with per-field and per-section copy buttons."""

    def __init__(self, sections=None, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.separator_height = 0
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.size_hint = (0.95, 0.93)
        self._build_ui(sections or {})

    @staticmethod
    def _sections_to_text(sections):
        lines = []
        for title, items in sections.items():
            lines.append(f"\n=== {title} ===")
            lines.extend(items)
        return "\n".join(lines).strip()

    @staticmethod
    def _copy_toast(text):
        Clipboard.copy(text)
        core.toast("Copied to clipboard!")

    def _make_copy_btn(self, text, width=dp(72), color=(0.2, 0.45, 0.9, 1)):
        box = BoxLayout(size_hint=(None, None), width=width, height=dp(30), spacing=dp(2))
        icon = Button(text="📋", font_name='EmojiFont',
                      size_hint=(None, None), width=dp(22), height=dp(30),
                      background_normal='', background_down='', background_color=(0,0,0,0),
                      color=color, font_size='13sp')
        lbl  = Button(text="Copy", size_hint=(None, None), width=width-dp(24), height=dp(30),
                      background_normal='', background_down='', background_color=(0,0,0,0),
                      color=color, font_size='12sp')
        icon.bind(on_release=lambda x, t=text: self._copy_toast(t))
        lbl.bind(on_release=lambda x, t=text: self._copy_toast(t))
        box.add_widget(icon)
        box.add_widget(lbl)
        return box

    def _build_ui(self, sections):
        outer = BoxLayout(orientation='vertical', padding=0, spacing=0)
        with outer.canvas.before:
            Color(0.95, 0.96, 0.98, 1)
            self._bg = RoundedRectangle(pos=outer.pos, size=outer.size, radius=[dp(20)])
        outer.bind(pos=lambda _, v: setattr(self._bg, 'pos', v),
                   size=lambda _, v: setattr(self._bg, 'size', v))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(62), padding=[dp(14), dp(6), dp(10), 0], spacing=dp(4))
        hdr.add_widget(Label(text="📊", font_name='EmojiFont', font_size='22sp',
                             color=(0.2,0.45,0.9,1), size_hint=(None,None), width=dp(30), height=dp(50), valign='middle'))
        hdr.add_widget(Label(text="PDF Metadata Report", font_size='17sp', bold=True,
                             color=(0.2,0.45,0.9,1), halign='left', valign='middle',
                             size_hint_x=1, text_size=(Window.width*0.55, None)))
        hdr.add_widget(self._make_copy_btn(self._sections_to_text(sections), width=dp(76)))
        outer.add_widget(hdr)

        sep = BoxLayout(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(0.82, 0.85, 0.90, 1)
            Rectangle(pos=sep.pos, size=sep.size)
        outer.add_widget(sep)

        sv = ScrollView(do_scroll_x=False, bar_width=dp(4))
        content = BoxLayout(orientation='vertical', spacing=dp(10),
                            padding=[dp(12), dp(10), dp(12), dp(10)], size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        for sec_title, items in sections.items():
            content.add_widget(self._build_section(sec_title, items))
        sv.add_widget(content)
        outer.add_widget(sv)

        btn_row = BoxLayout(size_hint_y=None, height=dp(62), padding=[dp(20), dp(8)])
        close_btn = Button(text="CLOSE", background_normal='', background_down='',
                           background_color=(0,0,0,0), color=(1,1,1,1), font_size='15sp', bold=True)
        with close_btn.canvas.before:
            Color(0.2, 0.45, 0.9, 1)
            self._close_bg = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[dp(24)])
        close_btn.bind(pos=lambda _, v: setattr(self._close_bg, 'pos', v),
                       size=lambda _, v: setattr(self._close_bg, 'size', v),
                       on_release=lambda _: self.dismiss())
        btn_row.add_widget(close_btn)
        outer.add_widget(btn_row)
        self.add_widget(outer)

    def _build_section(self, title, items):
        sec = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        sec.bind(minimum_height=sec.setter('height'))

        parts = title.split(' ', 1)
        emoji_char = parts[0] if len(parts) == 2 else ''
        title_text = parts[1] if len(parts) == 2 else title

        sec_hdr = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        sec_hdr.add_widget(Label(text=emoji_char, font_name='EmojiFont', font_size='16sp',
                                 color=(0.15,0.38,0.80,1), size_hint=(None,None), width=dp(24), height=dp(38), valign='middle'))
        sec_hdr.add_widget(Label(text=title_text, font_size='13sp', bold=True,
                                 color=(0.15,0.38,0.80,1), halign='left', valign='middle',
                                 size_hint_x=1, text_size=(Window.width*0.55, dp(38))))
        sec_hdr.add_widget(self._make_copy_btn("\n".join(items), width=dp(72)))
        sec.add_widget(sec_hdr)

        card = BoxLayout(orientation='vertical', size_hint_y=None,
                         padding=[dp(12), dp(8), dp(4), dp(8)], spacing=dp(1))
        card.bind(minimum_height=card.setter('height'))
        with card.canvas.before:
            Color(1, 1, 1, 1)
            card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        card.bind(pos=lambda _, v: setattr(card_bg, 'pos', v),
                  size=lambda _, v: setattr(card_bg, 'size', v))

        for raw_item in items:
            stripped = raw_item.strip()
            if not stripped: continue
            row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
            lbl = Label(text=stripped, font_size='12.5sp', color=(0.13,0.16,0.20,1),
                        halign='left', valign='middle', size_hint_x=1)
            lbl.bind(
                width=lambda inst, val: setattr(inst, 'text_size', (max(val-dp(4), dp(10)), None)),
                texture_size=lambda inst, val: setattr(inst.parent, 'height', max(val[1]+dp(8), dp(30))) if inst.parent else None,
            )
            copy_icon = Button(text="📋", font_name='EmojiFont',
                               size_hint=(None,None), width=dp(30), height=dp(28),
                               background_normal='', background_down='', background_color=(0,0,0,0),
                               color=(0.55,0.58,0.65,1), font_size='14sp')
            copy_icon.bind(on_release=lambda x, t=stripped: self._copy_toast(t))
            row.add_widget(lbl)
            row.add_widget(copy_icon)
            card.add_widget(row)

        sec.add_widget(card)
        return sec


# ── FilePopup ─────────────────────────────────────────────────────────────────

class FilePopup(Popup):
    load       = ObjectProperty(None)
    filters    = ListProperty(['*'])
    multiselect = ObjectProperty(False)


# ── ExtractedTextPopup ────────────────────────────────────────────────────────

class ExtractedTextPopup(Popup):
    """Scrollable viewer for extracted text with copy functionality."""

    def __init__(self, text="", filename="", **kwargs):
        super().__init__(**kwargs)
        self.title            = ""
        self.separator_height = 0
        self.background       = ""
        self.background_color = (0, 0, 0, 0)
        self.size_hint        = (1, 1)
        self._text            = text
        self._filename        = filename
        self._build_ui()

    def _build_ui(self):
        outer = BoxLayout(orientation='vertical')
        with outer.canvas.before:
            Color(0.95, 0.96, 0.98, 1)
            self._bg = Rectangle(pos=outer.pos, size=outer.size)
        outer.bind(pos=lambda _, v: setattr(self._bg, 'pos', v),
                   size=lambda _, v: setattr(self._bg, 'size', v))

        # Header bar
        hdr = BoxLayout(size_hint_y=None, height=dp(58),
                        padding=[dp(14), dp(8), dp(10), dp(8)], spacing=dp(8))
        with hdr.canvas.before:
            Color(0.2, 0.45, 0.9, 1)
            hdr_bg = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda _, v: setattr(hdr_bg, 'pos', v),
                 size=lambda _, v: setattr(hdr_bg, 'size', v))

        fname_short = self._filename[:30] + "…" if len(self._filename) > 30 else self._filename
        hdr.add_widget(Label(
            text=f"[b]Extracted Text[/b]  —  {fname_short}", markup=True,
            font_size='14sp', color=(1,1,1,1), halign='left', valign='middle',
            size_hint_x=1, text_size=(Window.width*0.6, None)))

        copy_hdr_btn = Button(
            text="Copy All", size_hint=(None, None), width=dp(82), height=dp(38),
            background_normal='', background_down='', background_color=(1,1,1,0.2),
            color=(1,1,1,1), font_size='13sp', bold=True)
        copy_hdr_btn.bind(on_release=lambda _: self._copy_all())
        hdr.add_widget(copy_hdr_btn)

        close_btn = Button(
            text="✕", size_hint=(None, None), width=dp(38), height=dp(38),
            background_normal='', background_down='', background_color=(1,1,1,0.15),
            color=(1,1,1,1), font_size='20sp', bold=True)
        close_btn.bind(on_release=lambda _: self.dismiss())
        hdr.add_widget(close_btn)
        outer.add_widget(hdr)

        # Stats bar
        words = len(self._text.split())
        chars = len(self._text)
        stats = Label(
            text=f"{words:,} words  |  {chars:,} characters",
            font_size='12sp', color=(0.4, 0.45, 0.55, 1),
            size_hint_y=None, height=dp(30),
            halign='center', valign='middle')
        outer.add_widget(stats)

        # Scrollable text body
        sv = ScrollView(do_scroll_x=False, bar_width=dp(5))
        body = Label(
            text=self._text,
            font_size='13sp', color=(0.1, 0.12, 0.14, 1),
            halign='left', valign='top',
            size_hint_y=None, padding=[dp(16), dp(12)],
            markup=False)
        body.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        body.bind(width=lambda inst, val: setattr(inst, 'text_size', (val - dp(32), None)))
        sv.add_widget(body)
        outer.add_widget(sv)

        # Bottom copy button
        footer = BoxLayout(size_hint_y=None, height=dp(62), padding=[dp(16), dp(8)])
        copy_btn = Button(
            text="Copy All Text",
            background_normal='', background_down='', background_color=(0,0,0,0),
            color=(1,1,1,1), font_size='15sp', bold=True)
        with copy_btn.canvas.before:
            Color(0.1, 0.55, 0.3, 1)
            cb_bg = RoundedRectangle(pos=copy_btn.pos, size=copy_btn.size, radius=[dp(24)])
        copy_btn.bind(pos=lambda _, v: setattr(cb_bg, 'pos', v),
                      size=lambda _, v: setattr(cb_bg, 'size', v),
                      on_release=lambda _: self._copy_all())
        footer.add_widget(copy_btn)
        outer.add_widget(footer)

        self.add_widget(outer)

    def _copy_all(self):
        Clipboard.copy(self._text)
        core.toast("Text copied to clipboard!")
