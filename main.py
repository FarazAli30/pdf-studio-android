"""
main.py
-------
PDF Studio — Entry point.
Run with:  python main.py
Android:   buildozer android debug deploy run
"""

import os
import sys
import logging

# ── Make project root importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ── Kivy imports (must come before config side-effects) ───────────────────────
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.properties import StringProperty
from kivy.utils import platform
from kivy.clock import Clock

# ── Project modules ───────────────────────────────────────────────────────────
import core.config  # side-effects: window colour, font registration, logging
from core.toast import core
from ui.kv_layout import KV
from screens import (
    MenuScreen,
    CompressScreen, PdfToImagesScreen, ImageToPDFScreen,
    MergeScreen, SplitScreen, RotateScreen, WatermarkScreen,
    EncryptScreen, InfoScreen, PageNumberScreen, HeaderFooterScreen,
    EnhancedExtractScreen, RepairScreen, RedactScreen,
)
from ui.popups import InfoPopup

# Android-only imports
if platform == "android":
    from android.activity import bind                          # type: ignore
    from jnius import autoclass, cast                          # type: ignore
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent         = autoclass('android.content.Intent')
    Uri            = autoclass('android.net.Uri')


class PDFStudioApp(App):
    session_file = StringProperty(None, allownone=True)

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self):
        self.RESULT_CODE_OPEN_DOC = 42
        self.RESULT_CODE_SAVE_DOC = 43
        self.saf_callback         = None
        self.temp_save_source     = None

        if platform == "android":
            bind(on_activity_result=self.on_activity_result)

        Builder.load_string(KV)
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CompressScreen(name='compress'))
        sm.add_widget(PdfToImagesScreen(name='pdf2img'))
        sm.add_widget(ImageToPDFScreen(name='img2pdf'))
        sm.add_widget(MergeScreen(name='merge'))
        sm.add_widget(SplitScreen(name='split'))
        sm.add_widget(RotateScreen(name='rotate'))
        sm.add_widget(WatermarkScreen(name='watermark'))
        sm.add_widget(EncryptScreen(name='encrypt'))
        sm.add_widget(InfoScreen(name='info'))
        sm.add_widget(PageNumberScreen(name='pagenum'))
        sm.add_widget(HeaderFooterScreen(name='headerfooter'))
        sm.add_widget(EnhancedExtractScreen(name='extract_plus'))
        sm.add_widget(RepairScreen(name='repair'))
        sm.add_widget(RedactScreen(name='redact'))
        return sm

    # ── Session management ────────────────────────────────────────────────────

    def update_session_file(self, file_path):
        if file_path and os.path.exists(file_path):
            self.session_file = file_path

    def clear_session(self):
        self.session_file = None
        core.toast("Session cleared")

    def save_session_file(self):
        if self.session_file:
            if platform == 'android':
                self.save_file_saf(self.session_file, os.path.basename(self.session_file))
            else:
                InfoPopup(message=f"File at:\n{self.session_file}").open()

    # ── GitHub link ───────────────────────────────────────────────────────────

    def open_github(self):
        from core.config import GITHUB_URL
        if platform == "android":
            try:
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(GITHUB_URL))
                activity = cast('android.app.Activity', PythonActivity.mActivity)
                activity.startActivity(intent)
            except Exception as e:
                InfoPopup(message=f"Could not open browser:\n{e}").open()
        else:
            import webbrowser
            webbrowser.open(GITHUB_URL)
            core.toast("Opening GitHub…")

    # ── SAF file picker (Android) ─────────────────────────────────────────────

    def select_files_saf(self, mime_type, multiselect, callback):
        self.saf_callback = callback
        if platform == 'android':
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType(mime_type)
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, multiselect)
            cast('android.app.Activity', PythonActivity.mActivity)\
                .startActivityForResult(intent, self.RESULT_CODE_OPEN_DOC)

    def save_file_saf(self, source_path, filename):
        self.temp_save_source = source_path
        if platform == 'android':
            mime = "application/pdf"
            if filename.endswith(".txt"):  mime = "text/plain"
            elif filename.endswith(".zip"): mime = "application/zip"
            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType(mime)
            intent.putExtra(Intent.EXTRA_TITLE, filename)
            cast('android.app.Activity', PythonActivity.mActivity)\
                .startActivityForResult(intent, self.RESULT_CODE_SAVE_DOC)

    def on_activity_result(self, request_code, result_code, intent):
        if request_code == self.RESULT_CODE_OPEN_DOC and result_code == -1:
            clip  = intent.getClipData()
            uris  = [clip.getItemAt(i).getUri() for i in range(clip.getItemCount())] \
                    if clip else [intent.getData()]
            self.process_selected_uris(uris)
        elif request_code == self.RESULT_CODE_SAVE_DOC and result_code == -1:
            self.write_to_uri(intent.getData(), self.temp_save_source)

    def write_to_uri(self, uri, source_path):
        try:
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            cr       = activity.getContentResolver()
            with open(source_path, 'rb') as f: data = f.read()
            out = cr.openOutputStream(uri)
            out.write(data); out.close()
            Clock.schedule_once(lambda dt: (core.toast("File saved!"), InfoPopup(message="File Saved!").open()), 0)
        except Exception as e:
            logging.error(f"SAF Save Error: {e}")
            Clock.schedule_once(lambda dt: InfoPopup(message=f"Save Failed:\n{e}").open(), 0)

    def process_selected_uris(self, uris):
        selected = []
        try:
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            cr       = activity.getContentResolver()
            for i, uri in enumerate(uris):
                mime = cr.getType(uri)
                ext  = ".pdf"
                if mime:
                    if "png"  in mime.lower(): ext = ".png"
                    elif "jpeg" in mime.lower() or "jpg" in mime.lower(): ext = ".jpg"
                cache = os.path.join(self.user_data_dir, f"saf_file_{i}{ext}")
                stream = cr.openInputStream(uri)
                buf = bytearray(4096)
                with open(cache, 'wb') as f:
                    while True:
                        n = stream.read(buf, 0, len(buf))
                        if n == -1: break
                        f.write(buf[:n])
                stream.close()
                if os.path.exists(cache):
                    selected.append(cache)
            if selected and self.saf_callback:
                Clock.schedule_once(lambda dt: self.saf_callback(selected), 0.1)
        except Exception as e:
            logging.error(f"SAF Error: {e}")


if __name__ == '__main__':
    PDFStudioApp().run()
