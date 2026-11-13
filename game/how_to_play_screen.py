"""How to play: the rules on one page. Reachable from the mode screen and the pause menu."""

import pygame

from common.constants import (
    SCREEN_WIDTH,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
    BACK_BUTTON_RECT,
    ROUNDS_TO_WIN,
    ROUND_TURN_LIMIT,
    TURN_TIME_LIMIT,
    SUDDEN_DEATH_TURN_LIMIT,
)
from game.button import Button
from game.screen_manager import Screen

SECTIONS = (
    ("Goal", [
        "Flick your pen so the other pen's centre slides off the board.",
    ]),
    ("Your turn", [
        "Click and hold on your pen, pull back, then release to flick.",
        f"You have {int(TURN_TIME_LIMIT)} seconds. If time runs out you lose that move.",
        "The dotted line and power bar show where and how hard you will flick.",
    ]),
    ("Winning", [
        f"Win {ROUNDS_TO_WIN} rounds to win the match (best of {ROUNDS_TO_WIN * 2 - 1}).",
        "The board shrinks after a warning. Stay away from the edge!",
        f"No fall after {ROUND_TURN_LIMIT} turns each is a draw. The first draw is replayed.",
        f"The next draw goes to sudden death: a tiny board and {SUDDEN_DEATH_TURN_LIMIT} turns each.",
        "Still a draw? The pen closer to the middle wins.",
    ]),
    ("Keys", [
        "ESC: pause menu     SPACE: next round     R: rematch after a match",
    ]),
)


class HowToPlayScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = pygame.font.Font(None, FONT_SIZE_HEADING)
        self.section_font = pygame.font.Font(None, FONT_SIZE_BUTTON)
        self.font = pygame.font.Font(None, FONT_SIZE_SMALL + 4)
        self.back_btn = Button("Back", BACK_BUTTON_RECT, self.on_back)
        self.return_to = "mode_select"  # whoever opens this screen sets where Back goes

    def on_back(self) -> None:
        self.manager.switch(self.return_to)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.back_btn.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        heading = self.heading_font.render("How to Play", True, HEADING_COLOR)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        y = 130
        for title, lines in SECTIONS:
            surface.blit(self.section_font.render(title, True, HEADING_COLOR), (140, y))
            y += 36
            for line in lines:
                surface.blit(self.font.render(line, True, TEXT_COLOR), (170, y))
                y += 28
            y += 12
        self.back_btn.draw(surface)
