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


def _volume() -> float:
    """Music Off does not stop the song, it only turns the sound down to 0."""
    return MUSIC_VOLUME if settings.is_music_on() else 0.0


def _play() -> None:
    global _warned
    try:
        path = _find_track()
        if path is None:
            if os.path.exists(resource_path(MUSIC_BASE + ".mp4")):
                raise pygame.error("pygame cannot play .mp4 files. Convert the song to .mp3 or .ogg")
            raise pygame.error(f"no .ogg/.mp3/.wav file found at {MUSIC_BASE}")
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(_volume())
        pygame.mixer.music.play(-1)  # -1 = repeat forever
    except pygame.error as error:
        if not _warned:  # say it once, never crash the game over music
            print(f"Music not played: {error}")
            _warned = True


def _apply() -> None:
    if not _ready():
        return
    playing = pygame.mixer.music.get_busy()
    if _wanted and not playing:
        _play()
    elif not _wanted and playing:
        pygame.mixer.music.stop()
    pygame.mixer.music.set_volume(_volume())  # Off = silent, but the song keeps running


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


# ----- Sound Effects (SFX) -----

_sfx_cache: dict = {}


def play_sound(name: str, volume: float = 1.0) -> None:
    """Play a short sound effect if music/sound is on."""
    if not settings.is_music_on():
        return
    if not _ready():
        return
    try:
        if name not in _sfx_cache:
            for ext in (".mp3", ".wav", ".ogg"):
                path = resource_path(f"assets/sounds/{name}{ext}")
                if os.path.exists(path):
                    _sfx_cache[name] = pygame.mixer.Sound(path)
                    break
        sound = _sfx_cache.get(name)
        if sound:
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play()
    except Exception:
        pass
