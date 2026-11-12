"""Persistent user settings (music on/off). Never crashes on a bad file."""

import json
import os

from platformdirs import user_data_dir

from common.constants import SAVE_DIR_NAME, SETTINGS_FILE_NAME

DEFAULTS = {"music_on": True}

_settings = dict(DEFAULTS)


def _settings_path() -> str:
    folder = user_data_dir(SAVE_DIR_NAME, appauthor=False)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, SETTINGS_FILE_NAME)


def load() -> None:
    """Load settings from disk. Falls back to defaults on any problem."""
    global _settings
    _settings = dict(DEFAULTS)
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(data, dict) and isinstance(data.get("music_on"), bool):
        _settings["music_on"] = data["music_on"]


def _save() -> None:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(_settings, f, indent=2)
    except OSError:
        pass


def is_music_on() -> bool:
    return _settings["music_on"]


def set_music_on(value: bool) -> None:
    _settings["music_on"] = value
    _save()