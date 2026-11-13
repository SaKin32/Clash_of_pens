"""Mode selection screen: Player vs Computer, Player vs Player, Online."""

import pygame

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    VERSION,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    MODE_BUTTON_WIDTH,
    BACK_BUTTON_RECT,
)
from game import settings
from game.button import Button
from game.screen_manager import Screen


class ModeSelectScreen(Screen):
    """Lets the player choose how to play."""

    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = pygame.font.Font(None, FONT_SIZE_HEADING)
        self.small_font = pygame.font.Font(None, FONT_SIZE_SMALL)

        self.music_btn = Button(self._music_label(), self._rect(3), self.on_toggle_music)
        self.buttons = [
            Button("Player vs Computer", self._rect(0), self.on_pvc),
            Button("Player vs Player", self._rect(1), self.on_pvp),
            Button("Online", self._rect(2), self.on_online),
            self.music_btn,
        ]
        self.back_btn = Button("Back", BACK_BUTTON_RECT, self.on_back)

    @staticmethod
    def _rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - MODE_BUTTON_WIDTH) // 2
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, MODE_BUTTON_WIDTH, BUTTON_HEIGHT)

    @staticmethod
    def _music_label() -> str:
        return "Music: On" if settings.is_music_on() else "Music: Off"

    def on_enter(self) -> None:
        self.music_btn.text = self._music_label()

    # Mode callbacks (the actual modes are added in later steps)
    def on_pvc(self) -> None:
        self.manager.switch("match")

    def on_pvp(self) -> None:
        self.manager.switch("match")

    def on_online(self) -> None:
        print("Online selected")

    def on_toggle_music(self) -> None:
        settings.set_music_on(not settings.is_music_on())
        self.music_btn.text = self._music_label()

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