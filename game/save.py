"""Save and load game state. Never crashes on a missing or corrupt file."""

import json
import os
from typing import Optional

from platformdirs import user_data_dir

from common.constants import SAVE_DIR_NAME, SAVE_FILE_NAME, SAVE_VERSION

# Only these modes can be saved. Online matches cannot be resumed.
SAVABLE_MODES = ("pvc", "pvp")


def save_path() -> str:
    """Return the full path of the save file, creating the folder if needed."""
    folder = user_data_dir(SAVE_DIR_NAME, appauthor=False)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, SAVE_FILE_NAME)


def has_save() -> bool:
    """Return True if a valid save exists."""
    return load_game() is not None


def save_game(state: dict) -> bool:
    """Write the state to disk. Returns True on success."""
    data = {"version": SAVE_VERSION, "state": state}
    path = save_path()
    temp_path = path + ".tmp"
    try:
        # Write to a temp file first so a crash cannot leave a half-written save
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)
        return True
    except OSError:
        return False


def load_game() -> Optional[dict]:
    """Return the saved state, or None if missing, corrupt or invalid."""
    path = save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None

    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return None
    state = data.get("state")
    if not isinstance(state, dict) or state.get("mode") not in SAVABLE_MODES:
        return None
    return state


def delete_save() -> None:
    """Remove the save file if it exists."""
    try:
        os.remove(save_path())
    except OSError:
        pass