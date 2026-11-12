"""Reusable clickable button for menu screens."""

from typing import Callable, Optional

import pygame

from common.constants import (
    BUTTON_COLOR,
    BUTTON_HOVER_COLOR,
    BUTTON_DISABLED_COLOR,
    BUTTON_TEXT_COLOR,
    BUTTON_TEXT_DISABLED_COLOR,
    FONT_SIZE_BUTTON,
)


class Button:
    """A rectangular button with hover and disabled states."""

    def __init__(
        self,
        text: str,
        rect: tuple,
        on_click: Optional[Callable[[], None]] = None,
        enabled: bool = True,
        font_size: int = FONT_SIZE_BUTTON,
    ):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.on_click = on_click
        self.enabled = enabled
        self.font = pygame.font.Font(None, font_size)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Call on_click when the left mouse button is pressed on the button."""
        if not self.enabled:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.on_click:
                self.on_click()

    def draw(self, surface: pygame.Surface) -> None:
        hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        if not self.enabled:
            color, text_color = BUTTON_DISABLED_COLOR, BUTTON_TEXT_DISABLED_COLOR
        elif hovered:
            color, text_color = BUTTON_HOVER_COLOR, BUTTON_TEXT_COLOR
        else:
            color, text_color = BUTTON_COLOR, BUTTON_TEXT_COLOR

        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        label = self.font.render(self.text, True, text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))