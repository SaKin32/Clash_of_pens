"""Pictures used inside a match: the wooden table and the pen sprites.

Everything here returns None when a picture file is missing, so the match screen can fall back to plain shapes.
"""

from typing import Dict, Optional, Tuple

import pygame

from common.constants import BOARD_RECT
from game.assets import load_image
from game.pen_select_screen import PEN_IMAGES

TABLE_FILE = "table.png"
GLOW_PAD = 14        # how far the coloured player glow reaches past the pen
GLOW_ALPHA = 120     # how strong the player glow is (0-255)

_table: Optional[pygame.Surface] = None
_table_loaded = False
_sprites: Dict[Tuple[str, int, tuple], Optional[pygame.Surface]] = {}


def table_texture() -> Optional[pygame.Surface]:
    """table.png turned sideways and cropped to fill the whole board area (BOARD_RECT)."""
    global _table, _table_loaded
    if _table_loaded:
        return _table
    _table_loaded = True
    image = load_image(TABLE_FILE)
    if image is None:
        return None
    image = pygame.transform.rotate(image, 90)  # the wood grain runs left to right
    w, h = BOARD_RECT[2], BOARD_RECT[3]
    scale = max(w / image.get_width(), h / image.get_height())
    size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
    image = pygame.transform.smoothscale(image, size)
    _table = image.subsurface(((size[0] - w) // 2, (size[1] - h) // 2, w, h)).copy()
    return _table


def _trim(image: pygame.Surface) -> pygame.Surface:
    mask = pygame.mask.from_surface(image, 128)  # 128 skips faint stray pixels
    rects = mask.get_bounding_rects()
    if not rects:
        return image
    return image.subsurface(rects[0].unionall(rects[1:])).copy()


def _level(image: pygame.Surface) -> pygame.Surface:
    """Turn a slanted pen picture until the pen lies flat (tip to the right)."""
    angle = pygame.mask.from_surface(image, 128).angle()
    best, best_ratio = image, 0.0
    for degrees in (angle, -angle):
        turned = _trim(pygame.transform.rotate(image, degrees))
        ratio = turned.get_width() / turned.get_height()
        if ratio > best_ratio:
            best, best_ratio = turned, ratio
    return best


def pen_sprite(key: str, length: int, color: tuple) -> Optional[pygame.Surface]:
    """The pen picture lying flat, `length` pixels long, on a soft glow in the player's colour."""
    cache_key = (key, length, tuple(color))
    if cache_key in _sprites:
        return _sprites[cache_key]
    sprite = None
    name = PEN_IMAGES.get(key)
    image = load_image(name) if name else None
    if image is not None:
        flat = _level(_trim(image))
        height = max(1, round(flat.get_height() * length / flat.get_width()))
        flat = pygame.transform.smoothscale(flat, (length, height))
        sprite = pygame.Surface((length + 2 * GLOW_PAD, height + 2 * GLOW_PAD), pygame.SRCALPHA)
        pygame.draw.ellipse(sprite, tuple(color) + (GLOW_ALPHA,), sprite.get_rect())
        sprite.blit(flat, (GLOW_PAD, GLOW_PAD))
    _sprites[cache_key] = sprite
    return sprite