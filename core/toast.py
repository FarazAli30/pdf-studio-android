"""
toast.py
--------
Cross-platform toast / notification helper.
On Android uses native Toast; on desktop shows a brief ModalView.
"""

import logging
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.utils import platform


class Core:
    """Global helper — instantiated once as ``core`` at module level."""

    def toast(self, message: str):
        logging.info(f"TOAST: {message}")
        if platform == "android":
            self._android_toast(message)
        else:
            Clock.schedule_once(lambda dt: self._desktop_toast(message), 0)

    # ── Android ───────────────────────────────────────────────────────────────
    def _android_toast(self, message: str):
        try:
            _display_android_toast(message)
        except Exception as e:
            logging.error(f"Toast Error: {e}")

    # ── Desktop fallback ──────────────────────────────────────────────────────
    def _desktop_toast(self, message: str):
        view = ModalView(
            size_hint=(None, None),
            size=(dp(300), dp(50)),
            pos_hint={"center_x": 0.5, "y": 0.1},
            background_color=(0.2, 0.2, 0.2, 0.9),
            overlay_color=(0, 0, 0, 0),
            auto_dismiss=False,
        )
        view.add_widget(Label(text=message, font_size="14sp", color=(1, 1, 1, 1)))
        view.open()
        Clock.schedule_once(lambda dt: view.dismiss(), 2.0)


# ── Android-only helper (defined at module level so decorator works) ───────────
if platform == "android":
    from android.runnable import run_on_ui_thread  # type: ignore
    from jnius import autoclass, cast              # type: ignore

    @run_on_ui_thread
    def _display_android_toast(msg: str):
        Toast    = autoclass("android.widget.Toast")
        String   = autoclass("java.lang.String")
        Activity = autoclass("org.kivy.android.PythonActivity")
        context  = cast("android.content.Context", Activity.mActivity)
        Toast.makeText(context, String(msg), Toast.LENGTH_SHORT).show()
else:
    def _display_android_toast(msg: str):  # no-op on desktop
        pass


# ── Singleton ─────────────────────────────────────────────────────────────────
core = Core()
