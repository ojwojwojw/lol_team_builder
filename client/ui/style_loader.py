from pathlib import Path
import sys


CLIENT_ROOT = Path(__file__).resolve().parents[1]


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return CLIENT_ROOT / relative_path


def load_style(app):
    path = resource_path("styles/dark.qss")
    with open(path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
