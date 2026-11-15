"""Round-less picture button (an icon from assets/images) with the same size and click animation as the music icon.

Every icon in the game (back.png, ...) uses this class, so they all look and behave the same."""

import math
from typing import Callable

import pygame

from game.music_icon import ICON_SIZE, CLICK_TIME, CLICK_DEPTH, _fit

ACTION_DELAY = 0.18  # the click action runs this many seconds after the click, so the press can be seen


class IconButton:
    """Icon picture that shrinks and bounces when clicked, then runs on_click."""

    def __init__(self, image_name: str, position: tuple, on_click: Callable[[], None], size: int = ICON_SIZE):
        self.rect = pygame.Rect(position[0], position[1], size, size)
        self.on_click = on_click
        self.image = _fit(image_name, size)
        self.click_time = CLICK_TIME  # CLICK_TIME means "no animation running"
        self.pending = False          # waiting to run on_click after the press animation
        self._last_tick = pygame.time.get_ticks()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.pending:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.click_time = 0.0
            self.pending = True

    def _scale(self) -> float:
        p = self.click_time / CLICK_TIME
        return 1.0 - CLICK_DEPTH * math.exp(-5 * p) * math.cos(2.5 * math.pi * p) if p < 1 else 1.0

    def _placeholder(self) -> pygame.Surface:
        """Simple round arrow shown when the picture file is missing, so the button still works."""
        frame = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        w, h = self.rect.size
        pygame.draw.circle(frame, (40, 40, 40), (w // 2, h // 2), w // 2)
        pygame.draw.circle(frame, (255, 255, 255), (w // 2, h // 2), w // 2, 3)
        pygame.draw.lines(frame, (255, 255, 255), False, [(w * 0.58, h * 0.28), (w * 0.38, h * 0.5), (w * 0.58, h * 0.72)], 6)
        return frame

    def draw(self, surface: pygame.Surface) -> None:
        now = pygame.time.get_ticks()
        dt = min(0.1, (now - self._last_tick) / 1000)
        self._last_tick = now
        self.click_time = min(CLICK_TIME, self.click_time + dt)

        frame = self.image if self.image else self._placeholder()
        scale = self._scale()
        if abs(scale - 1.0) > 0.002:
            size = (max(1, round(frame.get_width() * scale)), max(1, round(frame.get_height() * scale)))
            frame = pygame.transform.smoothscale(frame, size)
        surface.blit(frame, frame.get_rect(center=self.rect.center))

        if self.pending and self.click_time >= ACTION_DELAY:
            self.pending = False
            self.on_click()