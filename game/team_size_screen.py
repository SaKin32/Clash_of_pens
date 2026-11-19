"""Team size screen for Team Match: 2 vs 2 or 3 vs 3 on one computer."""

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
    BACK_BUTTON_RECT,
)
from game import setup as game_setup
from game.badge_button import BadgeButton, outlined_text
from game.common_ui import make_back_button, make_music_icon
from game.screen_manager import Screen

SIZES = (
    (2, "2 vs 2", "Two pens each. Two players share one computer."),
)


class TeamSizeScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = load_font(FONT_SIZE_HEADING)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.background = load_cover_image("bg_img.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.buttons = [
            BadgeButton(label, self._rect(i), lambda n=size: self.choose(n))
            for i, (size, label, _) in enumerate(SIZES)
        ]
        self.back_btn = make_back_button(self.on_back)
        self.music_icon = make_music_icon()

    @staticmethod
    def _rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - MODE_BUTTON_WIDTH) // 2
        y = 260 + index * (BUTTON_HEIGHT + BUTTON_GAP + 20)
        return (x, y, MODE_BUTTON_WIDTH, BUTTON_HEIGHT)

    def choose(self, size: int) -> None:
        game_setup.set_team_size(size)
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
        heading = outlined_text(self.heading_font, "Team Match", HEADING_COLOR, outline=3)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        for (_, _, note), button in zip(SIZES, self.buttons):
            button.draw(surface)
            text = outlined_text(self.small_font, note, TEXT_COLOR, outline=2)
            surface.blit(text, text.get_rect(midtop=(SCREEN_WIDTH // 2, button.rect.bottom + 6)))
        self.back_btn.draw(surface)
        self.music_icon.draw(surface)
