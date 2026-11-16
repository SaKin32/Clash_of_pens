"""Pictures used inside a match: the wooden table and the pen sprites.

Everything here returns None when a picture file is missing, so the match screen can fall back to plain shapes.
"""

import math
from typing import Dict, Optional, Tuple

import pygame

from common.constants import BOARD_RECT
from game.assets import load_image
from game.pen_select_screen import PEN_IMAGES

TABLE_FILE = "table.png"

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


def _small(image: pygame.Surface, biggest: int = 160) -> pygame.Surface:
    """A shrunken copy of the picture, so the measuring below stays quick."""
    w, h = image.get_size()
    k = min(1.0, biggest / max(w, h))
    if k >= 1.0:
        return image
    return pygame.transform.smoothscale(image, (max(1, round(w * k)), max(1, round(h * k))))


def _pen_angle(image: pygame.Surface) -> float:
    """How many degrees the pen's long axis is tilted (clockwise on screen).

    This is measured here instead of using pygame's Mask.angle(), because on some
    computers Mask.angle() gives a wrong answer and the pen stays slanted.
    """
    small = _small(image)
    mask = pygame.mask.from_surface(small, 128)
    w, h = small.get_size()
    points = [(x, y) for y in range(h) for x in range(w) if mask.get_at((x, y))]
    if len(points) < 2:
        return 0.0
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    mu20 = sum((p[0] - cx) ** 2 for p in points)
    mu02 = sum((p[1] - cy) ** 2 for p in points)
    mu11 = sum((p[0] - cx) * (p[1] - cy) for p in points)
    return math.degrees(0.5 * math.atan2(2 * mu11, mu20 - mu02))


def _tip_is_on_the_left(flat: pygame.Surface) -> bool:
    """A pen gets thinner towards its tip, so the thinner end is the tip."""
    small = _small(flat)
    mask = pygame.mask.from_surface(small, 128)
    w, h = small.get_size()
    strip = max(1, round(w * 0.06))
    left = sum(mask.get_at((x, y)) for x in range(strip) for y in range(h))
    right = sum(mask.get_at((x, y)) for x in range(w - strip, w) for y in range(h))
    return left < right


def _level(image: pygame.Surface) -> pygame.Surface:
    """Turn a slanted pen picture until the pen lies flat (tip to the right)."""
    flat = _trim(pygame.transform.rotate(image, _pen_angle(image)))
    if flat.get_height() > flat.get_width():  # still standing up: lay it down
        flat = _trim(pygame.transform.rotate(flat, 90))
    if _tip_is_on_the_left(flat):
        flat = pygame.transform.rotate(flat, 180)
    return flat


def pen_sprite(key: str, length: int, width: int) -> Optional[pygame.Surface]:
    """The pen picture lying flat, exactly `length` x `width` pixels.

    That is the same size as the pen's hitbox, so what you see is what collides: a pen
    never looks like it climbs over another pen. (Keep length/width close to the shape
    of the picture in common/pen.py, or the picture will look stretched.)
    """
    cache_key = (key, length, width)
    if cache_key in _sprites:
        return _sprites[cache_key]
    sprite = None
    name = PEN_IMAGES.get(key)
    image = load_image(name) if name else None
    if image is not None:
        flat = _level(_trim(image))
        sprite = pygame.transform.smoothscale(flat, (max(1, length), max(1, width)))
    _sprites[cache_key] = sprite
    return sprite