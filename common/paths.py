"""Helpers for resolving file paths."""

import os
import sys


def resource_path(relative_path: str) -> str:
    """Return the absolute path of a bundled resource.

    Works both when running from source and from a PyInstaller executable.
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # PyInstaller temp directory
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)