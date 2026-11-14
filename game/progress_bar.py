"""Loading bar drawn with assets/images/progressbar.png (used by the splash and loading screens)."""

import pygame

from common.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR
from game.assets import load_image
from game.badge_button import outlined_text

BAR_FILE = "progressbar.png"
BAR_WIDTH = 250              # width of the bar on screen (height follows the picture's shape)
BAR_BOTTOM = SCREEN_HEIGHT - 48   # distance of the bar's bottom edge from the top of the window
FILL_COLOR = (255, 210, 0)  # colour that fills an empty (hollow) bar picture
ALPHA_THRESHOLD = 128         # pixels fainter than this count as empty
OUTLINE_KEEP = 0.5            # parts of the picture darker than this (x the body colour) are outlines and stay as they are
LABEL_GAP = 10                # space between the "Loading..." text and the bar

# fallback bar when the picture is missing
FALLBACK_BG = (50, 52, 60)
FALLBACK_RADIUS = 9
FALLBACK_HEIGHT = 18


def _load_picture():
    """The picture with empty borders trimmed and scaled to BAR_WIDTH. None if missing."""
    image = load_image(BAR_FILE)
    if image is None:
        return None
    mask = pygame.mask.from_surface(image, ALPHA_THRESHOLD)
    rects = mask.get_bounding_rects()
    if rects:
        solid = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        mask.to_surface(solid, setsurface=image, unsetcolor=(0, 0, 0, 0))
        image = solid.subsurface(rects[0].unionall(rects[1:])).copy()
    height = max(1, round(image.get_height() * BAR_WIDTH / image.get_width()))
    return pygame.transform.smoothscale(image, (BAR_WIDTH, height))


def _hollow_area(image: pygame.Surface):
    """If the middle of the picture is see-through (an empty frame), return that inner area, else None."""
    w, h = image.get_size()
    cx, cy = w // 2, h // 2
    if image.get_at((cx, cy)).a >= ALPHA_THRESHOLD:
        return None  # the middle is solid: it is a full-colour bar
    left = cx
    while left > 0 and image.get_at((left - 1, cy)).a < ALPHA_THRESHOLD:
        left -= 1
    right = cx
    while right < w - 1 and image.get_at((right + 1, cy)).a < ALPHA_THRESHOLD:
        right += 1
    top = cy
    while top > 0 and image.get_at((cx, top - 1)).a < ALPHA_THRESHOLD:
        top -= 1
    bottom = cy
    while bottom < h - 1 and image.get_at((cx, bottom + 1)).a < ALPHA_THRESHOLD:
        bottom += 1
    return pygame.Rect(left, top, right - left + 1, bottom - top + 1)


_yellow_cache = {}


def _luma(colour) -> float:
    return 0.299 * colour[0] + 0.587 * colour[1] + 0.114 * colour[2]


def _make_yellow(image: pygame.Surface):
    """Copy of a solid-colour bar picture whose body is recoloured yellow (shading and outline are kept).

    Returns (yellow_picture, first_x, last_x) where first_x..last_x is the body part inside the outline."""
    key = image.get_size()
    if key in _yellow_cache:
        return _yellow_cache[key]
    w, h = image.get_size()
    body = max(1.0, _luma(image.get_at((w // 2, h // 2))))
    yellow = image.copy()
    for y in range(h):
        for x in range(w):
            pixel = image.get_at((x, y))
            if pixel.a == 0:
                continue
            factor = _luma(pixel) / body
            if factor >= OUTLINE_KEEP:
                yellow.set_at((x, y), (min(255, int(FILL_COLOR[0] * factor)),
                                       min(255, int(FILL_COLOR[1] * factor)),
                                       min(255, int(FILL_COLOR[2] * factor)), pixel.a))
    row = h // 2
    inside = [x for x in range(w) if image.get_at((x, row)).a > 0 and _luma(image.get_at((x, row))) / body >= OUTLINE_KEEP]
    result = (yellow, inside[0] if inside else 0, inside[-1] if inside else w - 1)
    _yellow_cache[key] = result
    return result


class LoadingBar:
    """Draws "Loading... N%" and the bar. The bar fills from left to right INSIDE the picture."""

    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.picture = _load_picture()
        self.inner = _hollow_area(self.picture) if self.picture else None
        self.yellow = None
        if self.picture and not self.inner:  # solid-colour bar picture: it is the empty bar, a yellow copy fills it
            self.yellow, self.first_x, self.last_x = _make_yellow(self.picture)

    def draw(self, surface: pygame.Surface, progress: float) -> None:
        progress = max(0.0, min(1.0, progress))
        if self.picture:
            bar = self.picture.get_rect(midbottom=(SCREEN_WIDTH // 2, BAR_BOTTOM))
        else:
            bar = pygame.Rect(0, 0, BAR_WIDTH, FALLBACK_HEIGHT)
            bar.midbottom = (SCREEN_WIDTH // 2, BAR_BOTTOM)

        text = f"Loading...  {int(progress * 100)}%"
        label = outlined_text(self.font, text, (255, 255, 255))
        surface.blit(label, label.get_rect(midbottom=(bar.centerx, bar.top - LABEL_GAP)))

        if not self.picture:
            pygame.draw.rect(surface, FALLBACK_BG, bar, border_radius=FALLBACK_RADIUS)
            fill = bar.copy()
            fill.width = max(bar.height, int(bar.width * progress))
            pygame.draw.rect(surface, FILL_COLOR, fill, border_radius=FALLBACK_RADIUS)
            pygame.draw.rect(surface, TEXT_COLOR, bar, width=2, border_radius=FALLBACK_RADIUS)
        elif self.inner:  # empty frame: colour grows underneath, the frame picture goes on top
            fill = pygame.Rect(bar.left + self.inner.left, bar.top + self.inner.top,
                               int(self.inner.width * progress), self.inner.height)
            pygame.draw.rect(surface, FILL_COLOR, fill)
            surface.blit(self.picture, bar)
        else:  # solid-colour bar: the picture is the empty bar, its yellow copy is revealed from the left
            surface.blit(self.picture, bar)
            shown = bar.width if progress >= 1.0 else int(self.first_x + (self.last_x - self.first_x) * progress)
            if shown > 0:
                surface.blit(self.yellow, bar.topleft, area=pygame.Rect(0, 0, shown, bar.height))