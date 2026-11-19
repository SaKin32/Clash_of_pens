"""Difficulty screen for Player vs Computer: Easy, Medium or Hard."""

import pygame
from game.assets import load_font, load_cover_image

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    MODE_BUTTON_WIDTH,
)
from game import setup as game_setup
from game.ai import PROFILES
from game.badge_button import BadgeButton, outlined_text
from game.common_ui import make_back_button, make_music_icon
from game.screen_manager import Screen

DESCRIPTIONS = {
    "easy": "Aims roughly and makes mistakes. Good for learning.",
    "medium": "Plans its flicks but is not perfect.",
    "hard": "Plans carefully and rarely misses.",
}


class DifficultyScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = load_font(FONT_SIZE_HEADING)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.background = load_cover_image("bg_img.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.buttons = [
            BadgeButton(PROFILES[key].name, self._rect(i), lambda k=key: self.choose(k))
            for i, key in enumerate(PROFILES)
        ]
        self.back_btn = make_back_button(self.on_back)
        self.music_icon = make_music_icon()

    @staticmethod
    def _rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - MODE_BUTTON_WIDTH) // 2
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP + 20)
        return (x, y, MODE_BUTTON_WIDTH, BUTTON_HEIGHT)

    def choose(self, key: str) -> None:
        game_setup.setup.difficulty = key
        game_setup.setup.picking = 0
        self.manager.switch("pen_select")

    def on_back(self) -> None:
        self.manager.switch("mode_select")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        for button in self.buttons:
            button.handle_event(event)
        self.back_btn.handle_event(event)
        self.music_icon.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(BG_COLOR)
        heading = outlined_text(self.heading_font, "Select Difficulty", HEADING_COLOR, outline=3)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        for key, button in zip(PROFILES, self.buttons):
            button.draw(surface)
            note = outlined_text(self.small_font, DESCRIPTIONS[key], TEXT_COLOR, outline=2)
            surface.blit(note, note.get_rect(midtop=(SCREEN_WIDTH // 2, button.rect.bottom + 6)))
        self.back_btn.draw(surface)
        self.music_icon.draw(surface)
