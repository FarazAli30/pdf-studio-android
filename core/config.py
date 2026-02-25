"""
config.py
---------
Global constants, Material You colour palette, logging setup
and Kivy window/font initialisation.
"""

import logging
from kivy.core.window import Window
from kivy.core.text import LabelBase

# ── Material You Color Palette ────────────────────────────────────────────────
PRIMARY                 = (0.2,  0.45, 0.9,  1)
ON_PRIMARY              = (1,    1,    1,    1)
SURFACE                 = (0.95, 0.96, 0.98, 1)
ON_SURFACE              = (0.1,  0.12, 0.14, 1)
SURFACE_VARIANT         = (0.88, 0.9,  0.94, 1)
OUTLINE                 = (0.7,  0.73, 0.78, 1)
SECONDARY_CONTAINER     = (0.85, 0.9,  1,    1)
ON_SECONDARY_CONTAINER  = (0,    0.1,  0.2,  1)

# ── Developer info ─────────────────────────────────────────────────────────────
GITHUB_URL    = "https://github.com/FarazAli30"
DEVELOPER     = "Faraz Ali"
APP_VERSION   = "1.1.0"
APP_NAME      = "PDF Studio"

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ── Kivy window ────────────────────────────────────────────────────────────────
Window.clearcolor = SURFACE

# ── Custom emoji / icon font ───────────────────────────────────────────────────
# Priority order: icons.ttf in root → icons.ttf in assets/ → Android system fonts → default
_font_candidates = [
    "icons.ttf",                                          # root folder (recommended)
    "assets/icons.ttf",                                   # assets subfolder
    "/system/fonts/NotoColorEmoji.ttf",                   # Android emoji font
    "/system/fonts/DroidSansFallback.ttf",                # Android fallback
    "/system/fonts/Roboto-Regular.ttf",                   # Android Roboto
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",    # Linux desktop
]

_font_registered = False
for _path in _font_candidates:
    try:
        LabelBase.register(name="EmojiFont", fn_regular=_path)
        logging.info(f"EmojiFont registered from: {_path}")
        _font_registered = True
        break
    except Exception:
        continue

if not _font_registered:
    # Last resort: register EmojiFont as a copy of the default Kivy font
    # so font_name='EmojiFont' in KV never raises OSError
    try:
        from kivy.core.text import DEFAULT_FONT
        LabelBase.register(name="EmojiFont", fn_regular=DEFAULT_FONT)
        logging.warning("EmojiFont using Kivy default font — emojis may not render")
    except Exception as e:
        logging.error(f"Could not register EmojiFont at all: {e}")
