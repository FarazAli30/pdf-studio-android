"""
base.py
-------
BaseToolScreen — shared logic for all PDF tool screens.
"""

import os
import threading

from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty, BooleanProperty, NumericProperty
from kivy.utils import platform
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup

from core.toast import core
from ui.popups import InfoPopup, PDFPreviewPopup


class BaseToolScreen(Screen):
    tool_title    = StringProperty("Tool")
    tool_info     = StringProperty("Information about this tool.")
    status_message = StringProperty("No files selected")
    selected_files = ListProperty([])
    is_processing  = BooleanProperty(False)
    progress_value = NumericProperty(0)
    working_file   = StringProperty("", allownone=True)
    download_ready = BooleanProperty(False)

    def on_pre_enter(self):
        app = App.get_running_app()
        if app.session_file and os.path.exists(app.session_file):
            if self.name != 'img2pdf':
                self.load_session_file(app.session_file)

    def load_session_file(self, path):
        self.working_file  = path
        self.selected_files = [path]
        self.download_ready = True
        self.status_message = f"Loaded session:\n{os.path.basename(path)}"
        if self.name == 'merge':
            self.status_message = f"File 1: {os.path.basename(path)}\nSelect more to merge."

    def clear_session(self):
        App.get_running_app().clear_session()
        self.working_file   = ""
        self.selected_files = []
        self.download_ready = False
        self.status_message = "Session cleared."

    def show_dialog(self, msg):
        InfoPopup(message=msg).open()

    def open_file_browser(self, mime_type="application/pdf", multi=False):
        if platform == "android":
            App.get_running_app().select_files_saf(mime_type, multi, self.load_selection)
        else:
            from kivy.uix.filechooser import FileChooserListView
            from ui.popups import FilePopup
            filters = ['*.pdf'] if "pdf" in mime_type else ['*.jpg', '*.png', '*.jpeg']
            FilePopup(load=self.load_selection, filters=filters, multiselect=multi).open()

    def load_selection(self, selection):
        if selection:
            self.selected_files = selection
            self.working_file   = selection[0]
            self.download_ready = False
            if len(selection) == 1 and self.name != 'img2pdf':
                App.get_running_app().update_session_file(self.working_file)
            msg = f"{len(selection)} file(s) selected."
            self.status_message = msg
            core.toast(msg)
            if (len(selection) == 1
                    and self.working_file.lower().endswith('.pdf')
                    and self.name not in ('merge', 'img2pdf')):
                Clock.schedule_once(lambda dt: self.preview_file("Selected File Preview"), 0.3)
        for w in App.get_running_app().root_window.children:
            if isinstance(w, Popup): w.dismiss()

    def reset_merge_list(self):
        pass

    def preview_file(self, title="PDF Preview"):
        path = self.working_file
        if not path or not os.path.exists(path):
            return self.show_dialog("No file loaded.")
        if not path.lower().endswith('.pdf'):
            return self.show_dialog("Preview is only available for PDF files.")
        PDFPreviewPopup(pdf_path=path, title_text=title).open()

    def complete_process(self, success, result_path, msg="Success"):
        self.is_processing = False
        if success:
            core.toast("Finished!")
            if result_path:
                App.get_running_app().update_session_file(result_path)
                self.working_file   = result_path
                self.download_ready = True
                self.status_message = f"Done!\n{msg}"
                if result_path.lower().endswith('.pdf'):
                    Clock.schedule_once(lambda dt: self.preview_file("Processed Result"), 0.3)
            else:
                self.status_message = f"Done!\n{msg}"
        else:
            core.toast(f"Error: {msg}")
            self.show_dialog(f"Error: {msg}")

    def download_result(self):
        if not self.working_file or not os.path.exists(self.working_file):
            return core.toast("No file to download")
        if platform == 'android':
            App.get_running_app().save_file_saf(
                self.working_file, os.path.basename(self.working_file))
        else:
            self.show_dialog(f"File saved at:\n{self.working_file}")

    def run_in_thread(self, func, *args, **kwargs):
        self.is_processing  = True
        self.progress_value = 0

        def update_progress(val):
            Clock.schedule_once(lambda dt: setattr(self, 'progress_value', val), 0)

        def wrapper():
            try:
                kwargs['progress_callback'] = update_progress
                success, result, msg = func(*args, **kwargs)
                Clock.schedule_once(lambda dt: self.complete_process(success, result, msg), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.complete_process(False, None, str(e)), 0)

        threading.Thread(target=wrapper, daemon=True).start()
