"""
tools.py
--------
All concrete tool screen classes.
Each extends BaseToolScreen and overrides process_action().
"""

import os
import threading

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock

from .base import BaseToolScreen
from pdf.processor import PDFProcessor
from ui.popups import MetadataPopup, ExtractedTextPopup
from core.toast import core


# ── Compress ──────────────────────────────────────────────────────────────────

class CompressScreen(BaseToolScreen):
    tool_title = "Compress PDF"
    tool_info  = "Reduce PDF size by resampling internal images."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        self.scale_label   = Label(text="Image Scale: 50%", font_size='14sp',
                                   color=(0.1,0.12,0.14,1), size_hint_y=None, height=dp(20),
                                   halign='left', text_size=(Window.width-dp(40), None))
        self.scale_slider  = Slider(min=0.1, max=1.0, value=0.5, step=0.1, size_hint_y=None, height=dp(40))
        self.quality_label = Label(text="JPEG Quality: 60", font_size='14sp',
                                   color=(0.1,0.12,0.14,1), size_hint_y=None, height=dp(20),
                                   halign='left', text_size=(Window.width-dp(40), None))
        self.quality_slider = Slider(min=10, max=95, value=60, step=5, size_hint_y=None, height=dp(40))
        self.scale_slider.bind(value=self._update_labels)
        self.quality_slider.bind(value=self._update_labels)
        ia.add_widget(self.scale_label);  ia.add_widget(self.scale_slider)
        ia.add_widget(self.quality_label); ia.add_widget(self.quality_slider)

    def _update_labels(self, *_):
        self.scale_label.text   = f"Image Scale: {int(self.scale_slider.value*100)}%"
        self.quality_label.text = f"JPEG Quality: {int(self.quality_slider.value)}"

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        out = PDFProcessor.get_save_path(self.working_file, "Compressed")
        self.run_in_thread(PDFProcessor.compress_pdf_working, self.working_file, out,
                           scale_factor=self.scale_slider.value, quality=int(self.quality_slider.value))


# ── PDF → Images ──────────────────────────────────────────────────────────────

class PdfToImagesScreen(BaseToolScreen):
    tool_title = "PDF to Images"
    tool_info  = "Extract all images from the PDF into a downloadable ZIP archive."

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        self.run_in_thread(PDFProcessor.extract_images_to_zip, self.working_file)


# ── Images → PDF ──────────────────────────────────────────────────────────────

class ImageToPDFScreen(BaseToolScreen):
    tool_title = "Images to PDF"
    tool_info  = "Convert multiple images into a single A4 PDF document."
    A4_WIDTH_PX  = 540
    A4_HEIGHT_PX = 720

    def open_file_browser(self): super().open_file_browser('image/*', True)

    def process_action(self):
        if not self.selected_files: return self.show_dialog("Please select images first.")
        self.status_message = "Generating A4 PDF..."
        self.is_processing  = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        from PIL import Image
        try:
            resample = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
            pages, total = [], len(self.selected_files)
            for idx, f in enumerate(self.selected_files):
                try:
                    img  = Image.open(f).convert('RGB')
                    page = Image.new('RGB', (self.A4_WIDTH_PX, self.A4_HEIGHT_PX), (255,255,255))
                    img.thumbnail((self.A4_WIDTH_PX, self.A4_HEIGHT_PX), resample)
                    page.paste(img, ((self.A4_WIDTH_PX-img.width)//2, (self.A4_HEIGHT_PX-img.height)//2))
                    pages.append(page)
                except Exception as e:
                    import logging; logging.error(f"Skip {f}: {e}")
                Clock.schedule_once(lambda dt, v=((idx+1)/total*90): setattr(self,'progress_value',v), 0)
            if not pages: raise Exception("No valid images.")
            out = PDFProcessor.get_save_path(self.selected_files[0], "Gallery")
            pages[0].save(out, save_all=True, append_images=pages[1:])
            Clock.schedule_once(lambda dt: setattr(self,'progress_value',100), 0)
            Clock.schedule_once(lambda dt: self.complete_process(True, out), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.complete_process(False, None, str(e)), 0)


# ── Merge ─────────────────────────────────────────────────────────────────────

class MergeScreen(BaseToolScreen):
    tool_title = "Merge Documents"
    tool_info  = "Combine multiple PDF documents into a single file."

    def open_file_browser(self): super().open_file_browser('application/pdf', True)

    def load_selection(self, selection):
        if selection:
            new = self.selected_files + [f for f in selection if f not in self.selected_files]
            self.selected_files = new
            if self.selected_files and not self.working_file:
                self.working_file = self.selected_files[0]
            self.download_ready  = False
            self.status_message  = f"{len(self.selected_files)} files selected."
            core.toast(f"Total: {len(self.selected_files)} files")
        from kivy.uix.popup import Popup
        from kivy.app import App
        for w in App.get_running_app().root_window.children:
            if isinstance(w, Popup): w.dismiss()

    def reset_merge_list(self):
        self.selected_files = []; self.working_file = ""
        self.status_message = "List cleared."; core.toast("List Cleared")

    def process_action(self):
        if len(self.selected_files) < 2: return self.show_dialog("Select at least 2 PDFs.")
        self.run_in_thread(PDFProcessor.merge_pdfs, self.selected_files)


# ── Split ─────────────────────────────────────────────────────────────────────

class SplitScreen(BaseToolScreen):
    tool_title = "Split Document"
    tool_info  = "Extract pages (e.g. 1, 3, 5-10)."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Enter Pages:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        self.ti = TextInput(hint_text="Page Range", size_hint_y=None, height=dp(50),
                            multiline=False, padding=[dp(10),dp(15)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.ti)

    def process_action(self):
        if not self.working_file or not self.ti.text: return self.show_dialog("Missing file or page range.")
        self.run_in_thread(PDFProcessor.split_pdf, self.working_file, self.ti.text)


# ── Rotate ────────────────────────────────────────────────────────────────────

class RotateScreen(BaseToolScreen):
    tool_title     = "Rotate Pages"
    tool_info      = "Choose clockwise rotation angle."
    rotation_angle = StringProperty("90")

    def on_kv_post(self, obj):
        ia  = self.ids.input_area
        box = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=dp(50))
        ia.add_widget(Label(text="Select Rotation:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        for angle in ["90", "180", "270"]:
            btn = Builder.load_string(f"SecondaryButton:\n    text: '{angle}°'\n    on_release: app.root.get_screen('rotate').set_angle('{angle}')")
            box.add_widget(btn)
        ia.add_widget(box)

    def set_angle(self, angle):
        self.rotation_angle  = angle
        self.status_message  = f"Rotation set to {angle}°"

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        self.run_in_thread(PDFProcessor.rotate_pdf, self.working_file, self.rotation_angle)


# ── Watermark ─────────────────────────────────────────────────────────────────

class WatermarkScreen(BaseToolScreen):
    tool_title = "Watermark PDF"
    tool_info  = "Add a diagonal text overlay."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Overlay Text:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        self.ti = TextInput(hint_text="Watermark Text", size_hint_y=None, height=dp(50),
                            multiline=False, padding=[dp(10),dp(15)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.ti)

    def process_action(self):
        if not self.working_file or not self.ti.text: return self.show_dialog("Missing file or text.")
        self.run_in_thread(PDFProcessor.watermark_pdf, self.working_file, self.ti.text)


# ── Encrypt ───────────────────────────────────────────────────────────────────

class EncryptScreen(BaseToolScreen):
    tool_title = "Protect PDF"
    tool_info  = "Encrypt with a password."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Set Password:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        self.ti = TextInput(hint_text="Enter Password", password=True, size_hint_y=None, height=dp(50),
                            multiline=False, padding=[dp(10),dp(15)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.ti)

    def process_action(self):
        if not self.working_file or not self.ti.text: return self.show_dialog("Missing file or password.")
        self.run_in_thread(PDFProcessor.encrypt_pdf, self.working_file, self.ti.text)


# ── Metadata ──────────────────────────────────────────────────────────────────

class InfoScreen(BaseToolScreen):
    tool_title = "Metadata Viewer"
    tool_info  = "Analyze PDF properties, structure, fonts and content."

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")

        def get_meta(file, progress_callback=None):
            import os
            from datetime import datetime
            from pypdf import PdfReader
            try:
                if progress_callback: progress_callback(5)
                reader = PdfReader(file)
                if progress_callback: progress_callback(20)
                sections = {}

                file_bytes = os.path.getsize(file)
                basic = [
                    f"Filename: {os.path.basename(file)}",
                    f"File Size: {file_bytes/(1024*1024):.2f} MB  ({file_bytes:,} bytes)",
                    f"Pages: {len(reader.pages)}",
                    f"Encrypted: {'Yes' if reader.is_encrypted else 'No'}",
                ]
                try:
                    with open(file,'rb') as f: basic.append(f"PDF Header: {f.readline().decode('utf-8',errors='ignore').strip()}")
                except Exception: pass
                sections["📄 Basic File Info"] = basic
                if progress_callback: progress_callback(30)

                meta = reader.metadata
                doc_info = []
                if meta:
                    for k in ['/Title','/Author','/Subject','/Creator','/Producer','/Keywords']:
                        v = meta.get(k)
                        if v: doc_info.append(f"{k[1:]}: {v}")
                    for dk in ['/CreationDate','/ModDate']:
                        raw = meta.get(dk)
                        if raw:
                            try:
                                s = str(raw)
                                if s.startswith("D:") and len(s) >= 16:
                                    dt = datetime.strptime(s[2:16], "%Y%m%d%H%M%S")
                                    doc_info.append(f"{dk[1:]}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                else: doc_info.append(f"{dk[1:]}: {raw}")
                            except Exception: doc_info.append(f"{dk[1:]}: {raw}")
                if not doc_info: doc_info = ["No standard metadata found."]
                sections["📝 Document Info"] = doc_info
                if progress_callback: progress_callback(50)

                page_sizes = []
                for i, page in enumerate(reader.pages[:5]):
                    mb = page.mediabox
                    w_pt, h_pt = float(mb.width), float(mb.height)
                    w_mm, h_mm = w_pt*0.3528, h_pt*0.3528
                    rot = page.get('/Rotate', 0)
                    page_sizes.append(f"Page {i+1}: {w_pt:.0f}×{h_pt:.0f} pt  ({w_mm:.0f}×{h_mm:.0f} mm)  Rotation: {rot}°")
                if len(reader.pages) > 5: page_sizes.append(f"... ({len(reader.pages)-5} more pages)")
                sections["📐 Page Geometry"] = page_sizes
                if progress_callback: progress_callback(70)

                content_info = []
                check_pages = min(len(reader.pages), 10)
                has_images = has_forms = has_attach = has_annots = False
                fonts = set()
                catalog = reader.trailer.get('/Root', {})
                if hasattr(catalog,'get_object'): catalog = catalog.get_object()
                for i in range(check_pages):
                    page = reader.pages[i]
                    res  = page.get('/Resources',{})
                    if hasattr(res,'get_object'): res = res.get_object()
                    if res.get('/XObject'): has_images = True
                    if '/Font' in res:
                        fobj = res['/Font']
                        if hasattr(fobj,'get_object'): fobj = fobj.get_object()
                        for fn in fobj.keys(): fonts.add(fn)
                    if '/Annots' in page: has_annots = True
                if '/AcroForm' in catalog: has_forms = True
                content_info += [
                    f"Total Pages: {len(reader.pages)}",
                    f"Has Images / XObjects: {'Yes' if has_images else 'No'}",
                    f"Has Forms (AcroForm): {'Yes' if has_forms else 'No'}",
                    f"Has Annotations / Links: {'Yes' if has_annots else 'No'}",
                    f"Unique Font References: {len(fonts)}",
                ]
                sections["🔍 Content Analysis"] = content_info
                if progress_callback: progress_callback(100)
                return True, file, sections
            except Exception as e:
                return False, None, str(e)

        self.run_in_thread(get_meta, self.working_file)

    def complete_process(self, success, result_path, msg="Success"):
        super().complete_process(success, result_path, "Metadata loaded.")
        if success and isinstance(msg, dict):
            MetadataPopup(sections=msg).open()


# ── Page Numbers ──────────────────────────────────────────────────────────────

class PageNumberScreen(BaseToolScreen):
    tool_title = "Add Page Numbers"
    tool_info  = "Stamp page numbers on every page. Choose position, start number, prefix/suffix."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Position:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        pos_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(110))
        self.pos_var  = "bottom-center"
        self._pos_btns = {}
        for key, label in [("top-left","Top Left"),("top-center","Top Center"),("top-right","Top Right"),
                            ("bottom-left","Bot Left"),("bottom-center","Bot Center"),("bottom-right","Bot Right")]:
            btn = Builder.load_string(f"SecondaryButton:\n    text: '{label}'")
            btn.bind(on_release=lambda x, k=key: self._set_pos(k))
            self._pos_btns[key] = btn
            pos_grid.add_widget(btn)
        ia.add_widget(pos_grid)
        self._highlight_pos()

        ia.add_widget(Label(text="Start Number:", font_size='14sp', color=(0.1,0.12,0.14,1),
                            size_hint_y=None, height=dp(20), halign='left', text_size=(Window.width-dp(40),None)))
        self.start_input = TextInput(hint_text="1", text="1", multiline=False,
                                     size_hint_y=None, height=dp(46), input_filter='int', padding=[dp(10),dp(13)])
        ia.add_widget(self.start_input)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        self.prefix_input = TextInput(hint_text='Prefix e.g. "Page "', multiline=False, size_hint_x=0.5, padding=[dp(10),dp(13)])
        self.suffix_input = TextInput(hint_text='Suffix e.g. " of 10"', multiline=False, size_hint_x=0.5, padding=[dp(10),dp(13)])
        row.add_widget(self.prefix_input); row.add_widget(self.suffix_input)
        ia.add_widget(row)

    def _set_pos(self, key):
        self.pos_var = key; self._highlight_pos()

    def _highlight_pos(self):
        for key, btn in self._pos_btns.items():
            btn.background_color = (0.2,0.45,0.9,1) if key==self.pos_var else (0,0,0,0)
            btn.color = (1,1,1,1) if key==self.pos_var else (0,0.1,0.2,1)

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        try: start = int(self.start_input.text or "1")
        except ValueError: start = 1
        self.run_in_thread(PDFProcessor.add_page_numbers, self.working_file,
                           self.pos_var, start, 12, self.prefix_input.text, self.suffix_input.text)


# ── Header / Footer ───────────────────────────────────────────────────────────

class HeaderFooterScreen(BaseToolScreen):
    tool_title = "Header / Footer"
    tool_info  = "Add custom header/footer text to every page.\nUse {page} and {total} as tokens.\nExample footer: 'Page {page} of {total}'"

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Header Text (leave blank to skip):",
                            font_size='14sp', color=(0.1,0.12,0.14,1), size_hint_y=None, height=dp(20),
                            halign='left', text_size=(Window.width-dp(40),None)))
        self.header_input = TextInput(hint_text="e.g. My Company — Confidential",
                                      multiline=False, size_hint_y=None, height=dp(46),
                                      padding=[dp(10),dp(13)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.header_input)
        ia.add_widget(Label(text="Footer Text (leave blank to skip):",
                            font_size='14sp', color=(0.1,0.12,0.14,1), size_hint_y=None, height=dp(20),
                            halign='left', text_size=(Window.width-dp(40),None)))
        self.footer_input = TextInput(hint_text="e.g. Page {page} of {total}",
                                      multiline=False, size_hint_y=None, height=dp(46),
                                      padding=[dp(10),dp(13)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.footer_input)

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        if not self.header_input.text and not self.footer_input.text:
            return self.show_dialog("Please enter at least a header or footer.")
        self.run_in_thread(PDFProcessor.add_header_footer, self.working_file,
                           self.header_input.text, self.footer_input.text)


# ── Extract Text+ ─────────────────────────────────────────────────────────────

class EnhancedExtractScreen(BaseToolScreen):
    tool_title = "Extract Text+"
    tool_info  = "Enhanced text extraction with per-page word counts, paragraph detection, and a full summary report. After processing, tap VIEW & COPY TEXT to read the extracted content."

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        self.run_in_thread(PDFProcessor.extract_text_enhanced, self.working_file)

    def complete_process(self, success, result_path, msg="Success"):
        super().complete_process(success, result_path, msg)
        if success and result_path and result_path.endswith('.txt'):
            if not getattr(self, '_view_btn_added', False):
                view_btn = Button(
                    text="VIEW & COPY TEXT",
                    size_hint_y=None, height=dp(52),
                    background_normal='', background_down='',
                    background_color=(0.15, 0.55, 0.35, 1),
                    color=(1,1,1,1), font_size='15sp', bold=True,
                )
                with view_btn.canvas.before:
                    Color(0.15, 0.55, 0.35, 1)
                    rr = RoundedRectangle(pos=view_btn.pos, size=view_btn.size, radius=[dp(28)])
                view_btn.bind(
                    pos=lambda inst, v: setattr(rr, 'pos', v),
                    size=lambda inst, v: setattr(rr, 'size', v),
                    on_release=lambda _: self._open_text_popup(),
                )
                self.ids.input_area.add_widget(view_btn)
                self._view_btn_added = True
            self._last_txt_path = result_path
            Clock.schedule_once(lambda dt: self._open_text_popup(), 0.4)

    def _open_text_popup(self):
        path = getattr(self, '_last_txt_path', None) or self.working_file
        if not path or not os.path.exists(path) or not path.endswith('.txt'):
            return self.show_dialog("No extracted text file yet. Press PROCESS first.")
        try:
            with open(path, 'r', encoding='utf-8') as f: text = f.read()
            ExtractedTextPopup(text=text, filename=os.path.basename(path)).open()
        except Exception as e:
            self.show_dialog(f"Could not open file: {e}")

    def preview_file(self, title="Preview"):
        path = getattr(self, '_last_txt_path', None)
        if path and path.endswith('.txt') and os.path.exists(path):
            self._open_text_popup()
        else:
            super().preview_file(title)


# ── Repair ────────────────────────────────────────────────────────────────────

class RepairScreen(BaseToolScreen):
    tool_title = "Repair PDF"
    tool_info  = "Attempts to recover a damaged or corrupted PDF by reading it in non-strict mode and rewriting all recoverable pages."

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        self.run_in_thread(PDFProcessor.repair_pdf, self.working_file)


# ── Redact ────────────────────────────────────────────────────────────────────

class RedactScreen(BaseToolScreen):
    tool_title = "Redact Text"
    tool_info  = "Black out sensitive words or phrases on every page.\nEnter one keyword per line."

    def on_kv_post(self, obj):
        ia = self.ids.input_area
        ia.add_widget(Label(text="Keywords to Redact (one per line):",
                            font_size='14sp', color=(0.1,0.12,0.14,1), size_hint_y=None, height=dp(20),
                            halign='left', text_size=(Window.width-dp(40),None)))
        self.kw_input = TextInput(
            hint_text="e.g.\nconfidential\npassword\nJohn Doe",
            multiline=True, size_hint_y=None, height=dp(130),
            padding=[dp(10),dp(10)], background_normal='', background_color=(1,1,1,1))
        ia.add_widget(self.kw_input)

    def process_action(self):
        if not self.working_file: return self.show_dialog("Please select a PDF file.")
        raw = self.kw_input.text.strip()
        if not raw: return self.show_dialog("Please enter at least one keyword.")
        keywords = [k.strip() for k in raw.splitlines() if k.strip()]
        self.run_in_thread(PDFProcessor.redact_text, self.working_file, keywords)
