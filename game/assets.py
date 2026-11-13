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