"""Mode selection screen: Player vs Computer, Player vs Player, Online."""

import pygame

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    OVERLAY_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    VERSION,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    MODE_BUTTON_WIDTH,
    BACK_BUTTON_RECT,
)
from game.button import Button
from game.screen_manager import Screen


class ModeSelectScreen(Screen):
    """Lets the player choose how to play."""

    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = pygame.font.Font(None, FONT_SIZE_HEADING)
        self.small_font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.music_on = True

        self.buttons = [
            Button("Player vs Computer", self._rect(0), self.on_pvc),
            Button("Player vs Player", self._rect(1), self.on_pvp),
            Button("Online", self._rect(2), self.on_online),
            Button("Music: On", self._rect(3), self.on_toggle_music),
        ]
        self.music_btn = self.buttons[3]
        self.back_btn = Button("Back", BACK_BUTTON_RECT, self.on_back)

    @staticmethod
    def _rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - MODE_BUTTON_WIDTH) // 2
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, MODE_BUTTON_WIDTH, BUTTON_HEIGHT)

    # Mode callbacks (the actual modes are added in later steps)
    def on_pvc(self) -> None:
        print("Player vs Computer selected")

    def on_pvp(self) -> None:
        print("Player vs Player selected")

    def on_online(self) -> None:
        print("Online selected")

    def on_toggle_music(self) -> None:
        self.music_on = not self.music_on
        self.music_btn.text = "Music: On" if self.music_on else "Music: Off"

    def on_back(self) -> None:
        self.manager.switch("title")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        for button in self.buttons:
            button.handle_event(event)
        self.back_btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)

        heading = self.heading_font.render("Select Mode", True, HEADING_COLOR)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 160)))

        for button in self.buttons:
            button.draw(surface)
        self.back_btn.draw(surface)

        version = self.small_font.render(f"v{VERSION}", True, TEXT_COLOR)
        surface.blit(
            version, version.get_rect(bottomright=(SCREEN_WIDTH - 16, SCREEN_HEIGHT - 12))
        )