"""Menu music: starts on the loading screen and plays until a match begins."""

import os

import pygame

from common.paths import resource_path
from game import settings

MUSIC_BASE = "assets/sounds/wwe_BL_Track01"
MUSIC_EXTENSIONS = (".ogg", ".mp3", ".wav")  # pygame cannot play .mp4 files
MUSIC_VOLUME = 1.0

_wanted = False   # True while the menus are open: the music should be playing
_warned = False


def _ready() -> bool:
    """Make sure the sound system works. False when there is no audio device."""
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init()
    except pygame.error:
        return False
    return True


def _find_track():
    for extension in MUSIC_EXTENSIONS:
        path = resource_path(MUSIC_BASE + extension)
        if os.path.exists(path):
            return path
    return None


def _play() -> None:
    global _warned
    try:
        path = _find_track()
        if path is None:
            if os.path.exists(resource_path(MUSIC_BASE + ".mp4")):
                raise pygame.error("pygame cannot play .mp4 files. Convert the song to .mp3 or .ogg")
            raise pygame.error(f"no .ogg/.mp3/.wav file found at {MUSIC_BASE}")
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(-1)  # -1 = repeat forever
    except pygame.error as error:
        if not _warned:  # say it once, never crash the game over music
            print(f"Music not played: {error}")
            _warned = True


def _apply() -> None:
    if not _ready():
        return
    should_play = _wanted and settings.is_music_on()
    playing = pygame.mixer.music.get_busy()
    if should_play and not playing:
        _play()
    elif not should_play and playing:
        pygame.mixer.music.stop()


def start() -> None:
    """The menus are open: play the music (does nothing if it is already playing)."""
    global _wanted
    _wanted = True
    _apply()


def stop() -> None:
    """A match is starting: stop the music."""
    global _wanted
    _wanted = False
    _apply()


def refresh() -> None:
    """Call after the Music On/Off button changes the setting."""
    _apply()