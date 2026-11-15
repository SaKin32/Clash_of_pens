"""Ready-made pieces every menu screen shares: the Back icon (top-left) and the Music icon (bottom-left)."""

from typing import Callable

from common.constants import SCREEN_HEIGHT
from game import music, settings
from game.icon_button import IconButton
from game.music_icon import MusicIcon, ICON_SIZE

BACK_ICON_FILE = "back.png"
BACK_ICON_POSITION = (20, 20)                                 # top-left corner of the window
MUSIC_ICON_POSITION = (20, SCREEN_HEIGHT - 20 - ICON_SIZE)    # bottom-left corner of the window


def make_back_button(on_click: Callable[[], None]) -> IconButton:
    """The Back icon. on_click says where Back goes."""
    return IconButton(BACK_ICON_FILE, BACK_ICON_POSITION, on_click)


def toggle_music() -> None:
    settings.set_music_on(not settings.is_music_on())
    music.refresh()


def make_music_icon() -> MusicIcon:
    """The Music icon: click to turn the music On/Off (grey while Off)."""
    return MusicIcon(MUSIC_ICON_POSITION, toggle_music)