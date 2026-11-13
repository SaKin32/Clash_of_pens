"""Shared test setup. Tests never open a window or touch the real save file."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Let tests import the game from the project root no matter where pytest is started
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture
def save_dir(tmp_path, monkeypatch):
    """Point the save system at a temporary folder."""
    import game.save as save

    monkeypatch.setattr(save, "user_data_dir", lambda *args, **kwargs: str(tmp_path))
    return tmp_path
