"""Menu button drawn with the assets/images/badge.png picture, with a press-and-bounce click animation."""

import math
from typing import Callable, Optional

import pygame

from game.assets import load_image
from game.button import Button

BADGE_FILE = "badge.png"
ALPHA_THRESHOLD = 128   # pixels fainter than this count as empty when trimming the picture
TEXT_COLOR = (255, 255, 255)
OUTLINE_COLOR = (0, 0, 0)
OUTLINE_SIZE = 2        # thickness of the black border around the letters, in pixels
DISABLED_TEXT_COLOR = (200, 200, 200)
DISABLED_LEVEL = 0.4    # how visible a disabled badge is (0 = invisible, 1 = normal)
HOVER_BRIGHTEN = 35     # extra brightness while the mouse is on the badge
CLICK_TIME = 0.5        # seconds the press-and-bounce animation lasts
CLICK_DEPTH = 0.12      # how much the badge shrinks when pressed
ACTION_DELAY = 0.18     # the click action runs this many seconds after the click, so the press can be seen

_cache = {}


def _load_badge(size: tuple) -> Optional[pygame.Surface]:
    """badge.png with its empty borders trimmed, stretched to size. None if the file is missing."""
    if size in _cache:
        return _cache[size]
    image = load_image(BADGE_FILE)
    if image is not None:
        mask = pygame.mask.from_surface(image, ALPHA_THRESHOLD)
        rects = mask.get_bounding_rects()
        if rects:
            solid = pygame.Surface(image.get_size(), pygame.SRCALPHA)
            mask.to_surface(solid, setsurface=image, unsetcolor=(0, 0, 0, 0))
            image = solid.subsurface(rects[0].unionall(rects[1:])).copy()
        image = pygame.transform.smoothscale(image, size)
    _cache[size] = image
    return image


def outlined_text(font: pygame.font.Font, text: str, color: tuple, outline: int = OUTLINE_SIZE) -> pygame.Surface:
    """Bold text with a solid black border."""
    base = font.render(text, True, color)
    dark = font.render(text, True, OUTLINE_COLOR)
    size = (base.get_width() + 2 * outline + 1, base.get_height() + 2 * outline)
    result = pygame.Surface(size, pygame.SRCALPHA)
    for dx in range(-outline, outline + 1):
        for dy in range(-outline, outline + 1):
            if dx * dx + dy * dy <= outline * outline + 1:
                for ex in (0, 1):
                    result.blit(dark, (outline + dx + ex, outline + dy))
    for ex in (0, 1):
        result.blit(base, (outline + ex, outline))
    return result


class BadgeButton(Button):
    """Same as Button, but drawn as the badge picture with white, thinly outlined text."""

    def __init__(self, text: str, rect: tuple, on_click: Optional[Callable[[], None]] = None,
                 enabled: bool = True, font_size: Optional[int] = None):
        if font_size is None:
            super().__init__(text, rect, on_click, enabled)
        else:
            super().__init__(text, rect, on_click, enabled, font_size)
        self.badge = _load_badge(self.rect.size)
        self.click_time = CLICK_TIME  # CLICK_TIME means "no animation running"
        self.pending = False          # waiting to run on_click after the press animation
        self._last_tick = pygame.time.get_ticks()

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.enabled or self.pending:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.click_time = 0.0
            self.pending = self.on_click is not None

    def _scale(self) -> float:
        p = self.click_time / CLICK_TIME
        return 1.0 - CLICK_DEPTH * math.exp(-5 * p) * math.cos(2.5 * math.pi * p) if p < 1 else 1.0

    def draw(self, surface: pygame.Surface) -> None:
        now = pygame.time.get_ticks()
        dt = min(0.1, (now - self._last_tick) / 1000)
        self._last_tick = now
        self.click_time = min(CLICK_TIME, self.click_time + dt)

        if self.badge is None:  # picture missing: use the normal button
            Button.draw(self, surface)
        else:
            hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
            frame = self.badge.copy()
            if hovered:
                frame.fill((HOVER_BRIGHTEN,) * 3 + (0,), special_flags=pygame.BLEND_RGB_ADD)
            if not self.enabled:
                frame.fill((255, 255, 255, int(255 * DISABLED_LEVEL)), special_flags=pygame.BLEND_RGBA_MULT)
            label = outlined_text(self.font, self.text, TEXT_COLOR if self.enabled else DISABLED_TEXT_COLOR)
            if not self.enabled:
                label.set_alpha(int(255 * (0.4 + 0.6 * DISABLED_LEVEL)))
            frame.blit(label, label.get_rect(center=frame.get_rect().center))
            scale = self._scale()
            if abs(scale - 1.0) > 0.002:
                size = (max(1, round(frame.get_width() * scale)), max(1, round(frame.get_height() * scale)))
                frame = pygame.transform.smoothscale(frame, size)
            surface.blit(frame, frame.get_rect(center=self.rect.center))

        if self.pending and self.click_time >= ACTION_DELAY:
            self.pending = False
            if self.on_click:
                self.on_click()