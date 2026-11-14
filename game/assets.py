"""Optional image loading. Returns None when a file is missing, so the game still runs."""

from typing import Optional

import pygame

from common.paths import resource_path

_cache = {}


def load_image(name: str, size: Optional[tuple] = None) -> Optional[pygame.Surface]:
    """Load assets/images/<name>, optionally scaled to size. None if missing."""
    key = (name, size)
    if key in _cache:
        return _cache[key]
    try:
        image = pygame.image.load(resource_path(f"assets/images/{name}")).convert_alpha()
        if size:
            image = pygame.transform.smoothscale(image, size)
    except (pygame.error, FileNotFoundError):
        image = None
    _cache[key] = image
    return image



def load_cover_image(name: str, size: tuple) -> Optional[pygame.Surface]:
    """Load assets/images/<name> so it fills size without stretching (extra edges are cropped)."""
    key = (name, size, "cover")
    if key in _cache:
        return _cache[key]
    image = load_image(name)
    result = None
    if image is not None:
        w, h = image.get_size()
        scale = max(size[0] / w, size[1] / h)
        scaled = pygame.transform.smoothscale(
            image, (max(1, round(w * scale)), max(1, round(h * scale)))
        )
        result = pygame.Surface(size).convert()
        result.blit(scaled, ((size[0] - scaled.get_width()) // 2, (size[1] - scaled.get_height()) // 2))
    _cache[key] = result
    return result

    

FONT_FILE = "assets/fonts/MotionControl-Bold.otf"
_fonts = {}


def load_font(size: int) -> pygame.font.Font:
    """The game font at the given size. Falls back to pygame's default font if the file is missing."""
    if size not in _fonts:
        try:
            _fonts[size] = pygame.font.Font(resource_path(FONT_FILE), size)
        except (OSError, pygame.error):
            _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]