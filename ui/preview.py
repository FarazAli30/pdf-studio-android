"""
preview.py
----------
PDFPreviewer  — renders PDF pages to raw RGBA bytes (background-thread safe).
PDFPreviewPopup — full-screen viewer with swipe navigation.
"""

import io
import logging
import threading

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.utils import platform
from kivy.clock import Clock
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont


class PDFPreviewer:
    """
    Renders a PDF page into raw RGBA bytes.
    Android: native PdfRenderer → ByteBuffer → bytes
    Desktop: pypdf + Pillow text fallback
    """

    @staticmethod
    def get_raw_android(pdf_path: str, page_index: int):
        from jnius import autoclass  # type: ignore
        PdfRenderer          = autoclass('android.graphics.pdf.PdfRenderer')
        ParcelFileDescriptor = autoclass('android.os.ParcelFileDescriptor')
        BitmapConfig         = autoclass('android.graphics.Bitmap$Config')
        Bitmap               = autoclass('android.graphics.Bitmap')
        ByteBuffer           = autoclass('java.nio.ByteBuffer')
        File                 = autoclass('java.io.File')

        pfd      = ParcelFileDescriptor.open(File(pdf_path), ParcelFileDescriptor.MODE_READ_ONLY)
        renderer = PdfRenderer(pfd)
        total    = renderer.getPageCount()
        page_index = max(0, min(page_index, total - 1))
        page     = renderer.openPage(page_index)
        w, h     = page.getWidth(), page.getHeight()
        bitmap   = Bitmap.createBitmap(w, h, BitmapConfig.ARGB_8888)
        page.render(bitmap, None, None, 1)
        page.close(); renderer.close(); pfd.close()

        buf = ByteBuffer.allocate(bitmap.getByteCount())
        bitmap.copyPixelsToBuffer(buf)
        return w, h, bytes(buf.array())

    @staticmethod
    def get_raw_fallback(pdf_path: str, page_index: int):
        PAGE_W     = 800
        reader     = PdfReader(pdf_path)
        total      = len(reader.pages)
        page_index = max(0, min(page_index, total - 1))
        page       = reader.pages[page_index]
        mb         = page.mediabox
        scale      = PAGE_W / float(mb.width)
        W, H       = PAGE_W, int(float(mb.height) * scale)

        img  = Image.new('RGBA', (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        try:
            res  = page.get('/Resources', {})
            if hasattr(res, 'get_object'): res = res.get_object()
            xobj = res.get('/XObject', {})
            if hasattr(xobj, 'get_object'): xobj = xobj.get_object()
            for key in (xobj or {}):
                obj = xobj[key]
                if hasattr(obj, 'get_object'): obj = obj.get_object()
                if obj.get('/Subtype') == '/Image':
                    try:
                        pil = Image.open(io.BytesIO(obj.get_data())).convert('RGBA').resize((W, H), Image.LANCZOS)
                        img.paste(pil, (0, 0))
                        img = Image.alpha_composite(img, Image.new('RGBA', (W, H), (255, 255, 255, 150)))
                        draw = ImageDraw.Draw(img)
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        font  = PDFPreviewer._fallback_font(13)
        small = PDFPreviewer._fallback_font(10)
        x0, y, line_h, max_w, max_y = 16, 16, 17, W - 24, H - 20
        raw_text = page.extract_text() or ""
        lines = raw_text.split('\n') if raw_text.strip() else ["(No selectable text on this page)"]

        for raw_line in lines:
            if y > max_y: break
            words, cur = raw_line.split(), ""
            for word in words:
                test = (cur + " " + word).strip()
                try:    tw = draw.textlength(test, font=font)
                except: tw = len(test) * 7
                if tw > max_w and cur:
                    draw.text((x0, y), cur, fill=(20, 20, 40, 255), font=font)
                    y += line_h; cur = word
                    if y > max_y: break
                else:
                    cur = test
            if cur and y <= max_y:
                draw.text((x0, y), cur, fill=(20, 20, 40, 255), font=font)
            y += line_h

        pnum = f"Page {page_index+1} of {total}  (desktop text preview)"
        draw.text((W//2 - len(pnum)*3, H - 14), pnum, fill=(150, 150, 165, 255), font=small)
        return W, H, img.tobytes('raw', 'RGBA')

    @staticmethod
    def _fallback_font(size):
        for path in ("Roboto-Regular.ttf", "/system/fonts/Roboto-Regular.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            try: return ImageFont.truetype(path, size)
            except: pass
        return ImageFont.load_default()

    @staticmethod
    def make_texture(w: int, h: int, raw_rgba: bytes):
        """Must be called on the main (UI) thread."""
        from kivy.graphics.texture import Texture
        tex = Texture.create(size=(w, h), colorfmt='rgba')
        tex.blit_buffer(raw_rgba, colorfmt='rgba', bufferfmt='ubyte')
        tex.flip_vertical()
        return tex


class PDFPreviewPopup(Popup):
    """Full-screen PDF viewer with swipe navigation and page cache."""

    def __init__(self, pdf_path: str, title_text: str = "Preview", **kwargs):
        super().__init__(**kwargs)
        self.pdf_path    = pdf_path
        self.title       = ""
        self.separator_height = 0
        self.background  = ""
        self.background_color = (0, 0, 0, 0)
        self.size_hint   = (1, 1)
        self._page_idx   = 0
        self._total      = 0
        self._title_text = title_text
        self._cache      = {}
        self._loading    = False
        self._build_ui()
        Clock.schedule_once(lambda dt: self._init_pdf(), 0.05)

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(0.85, 0.85, 0.85, 1)
            self._root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda _, v: setattr(self._root_bg, 'pos', v),
                  size=lambda _, v: setattr(self._root_bg, 'size', v))

        # Top bar
        bar = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(12), dp(7)], spacing=dp(8))
        with bar.canvas.before:
            Color(0.12, 0.14, 0.17, 1)
            self._bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda _, v: setattr(self._bar_bg, 'pos', v),
                 size=lambda _, v: setattr(self._bar_bg, 'size', v))
        self._title_lbl = Label(text=self._title_text, font_size='15sp', color=(1,1,1,1), bold=True)
        close_btn = Button(text="✕", size_hint_x=None, width=dp(44),
                           background_normal='', background_color=(0.8,0.2,0.2,1),
                           color=(1,1,1,1), font_size='18sp', bold=True)
        close_btn.bind(on_release=lambda _: self.dismiss())
        bar.add_widget(self._title_lbl)
        bar.add_widget(close_btn)
        root.add_widget(bar)

        # Page display
        self._display_container = BoxLayout(padding=dp(20))
        self._img = KivyImage(fit_mode="contain")
        with self._img.canvas.before:
            self._paper_color = Color(1, 1, 1, 0)
            self._paper_rect  = Rectangle(size=(0, 0), pos=(0, 0))
        self._img.bind(size=self._update_paper_bg, pos=self._update_paper_bg, texture=self._update_paper_bg)
        self._touch_x = None
        self._img.bind(on_touch_down=self._on_touch_down, on_touch_up=self._on_touch_up)
        self._display_container.add_widget(self._img)
        root.add_widget(self._display_container)

        # Control bar
        ctrl = BoxLayout(size_hint_y=None, height=dp(70), padding=dp(10), spacing=dp(12))
        with ctrl.canvas.before:
            Color(0.12, 0.14, 0.17, 1)
            self._ctrl_bg = Rectangle(pos=ctrl.pos, size=ctrl.size)
        ctrl.bind(pos=lambda _, v: setattr(self._ctrl_bg, 'pos', v),
                  size=lambda _, v: setattr(self._ctrl_bg, 'size', v))
        self._prev_btn = self._nav_btn("<", self._go_prev, disabled=True)
        self._info_lbl = Label(text="Loading...", font_size='16sp', color=(1,1,1,1))
        self._next_btn = self._nav_btn(">", self._go_next, disabled=True)
        ctrl.add_widget(self._prev_btn)
        ctrl.add_widget(self._info_lbl)
        ctrl.add_widget(self._next_btn)
        root.add_widget(ctrl)
        self.add_widget(root)

    def _nav_btn(self, text, cb, disabled=False):
        btn = Button(text=text, size_hint_x=None, width=dp(55), disabled=disabled,
                     background_normal='', background_color=(0.1,0.4,0.8,1),
                     color=(1,1,1,1), font_size='18sp', bold=True)
        btn.bind(on_release=lambda _: cb())
        return btn

    def _update_paper_bg(self, instance, value):
        if not self._img.texture:
            self._paper_color.a = 0; return
        self._paper_color.a = 1
        tw, th = self._img.texture.size
        iw, ih = self._img.size
        if tw == 0 or th == 0: return
        ratio = min(iw/tw, ih/th)
        nw, nh = tw*ratio, th*ratio
        self._paper_rect.pos  = (self._img.x + (iw-nw)/2, self._img.y + (ih-nh)/2)
        self._paper_rect.size = (nw, nh)

    def _on_touch_down(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._touch_x = touch.x; return True

    def _on_touch_up(self, widget, touch):
        if self._touch_x is None: return False
        dx = touch.x - self._touch_x
        self._touch_x = None
        if   dx < -dp(50): self._go_next()
        elif dx >  dp(50): self._go_prev()
        return True

    def _init_pdf(self):
        try:
            self._total = len(PdfReader(self.pdf_path).pages)
            self._title_lbl.text = f"{self._title_text}  —  {self.pdf_path.split('/')[-1]}"
        except Exception as e:
            self._info_lbl.text = f"Error: {e}"; return
        self._show_page(0)

    def _show_page(self, idx: int):
        if self._loading or self._total == 0: return
        idx = max(0, min(idx, self._total - 1))
        self._page_idx = idx
        if idx in self._cache:
            self._apply_raw(*self._cache[idx]); self._update_nav(); return
        self._loading = True
        self._info_lbl.text = f"Rendering page {idx+1}..."
        self._img.opacity = 0.4

        def _bg():
            try:
                result = PDFPreviewer.get_raw_android(self.pdf_path, idx) \
                         if platform == 'android' \
                         else PDFPreviewer.get_raw_fallback(self.pdf_path, idx)
                Clock.schedule_once(lambda dt: self._on_raw_ready(idx, result), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_render_error(str(e)), 0)

        threading.Thread(target=_bg, daemon=True).start()
        for ni in [idx+1, idx-1]:
            if 0 <= ni < self._total and ni not in self._cache:
                def _pre(i=ni):
                    try:
                        self._cache[i] = PDFPreviewer.get_raw_android(self.pdf_path, i) \
                                         if platform == 'android' \
                                         else PDFPreviewer.get_raw_fallback(self.pdf_path, i)
                    except Exception: pass
                threading.Thread(target=_pre, daemon=True).start()

    def _on_raw_ready(self, idx, result):
        self._cache[idx] = result
        self._loading    = False
        self._img.opacity = 1
        if idx == self._page_idx:
            self._apply_raw(*result)
        self._update_nav()

    def _on_render_error(self, msg):
        self._loading = False
        self._img.opacity = 1
        self._info_lbl.text = f"Error: {msg}"

    def _apply_raw(self, w, h, raw):
        self._img.texture = PDFPreviewer.make_texture(w, h, raw)
        self._update_paper_bg(self._img, None)

    def _go_prev(self):
        if self._page_idx > 0: self._show_page(self._page_idx - 1)

    def _go_next(self):
        if self._page_idx < self._total - 1: self._show_page(self._page_idx + 1)

    def _update_nav(self):
        self._info_lbl.text = f"Page {self._page_idx+1} of {self._total}"
        at_start = self._page_idx == 0
        at_end   = self._page_idx >= self._total - 1
        self._prev_btn.disabled = at_start
        self._next_btn.disabled = at_end
        self._prev_btn.background_color = (0.3,0.3,0.35,1) if at_start else (0.1,0.4,0.8,1)
        self._next_btn.background_color = (0.3,0.3,0.35,1) if at_end   else (0.1,0.4,0.8,1)
