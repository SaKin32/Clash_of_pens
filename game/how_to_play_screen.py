"""How to play: the rules on one page. Reachable from the mode screen and the pause menu."""

import pygame
from game.assets import load_font, load_cover_image

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_HEADING,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
    ROUNDS_TO_WIN,
    ROUND_TURN_LIMIT,
    TURN_TIME_LIMIT,
    SUDDEN_DEATH_TURN_LIMIT,
)
from game.badge_button import outlined_text
from game.common_ui import make_back_button, make_music_icon
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
    ("Team Match (2 vs 2)", [
        "2 vs 2: teammates take turns flicking their assigned pen in order. A pen that falls is out.",
        "A team with no pens left loses the round. At the turn limit, more pens left wins.",
    ]),
    ("Keys", [
        "ESC: pause menu     SPACE: next round     R: rematch after a match",
    ]),
)


class HowToPlayScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = load_font(FONT_SIZE_HEADING)
        self.section_font = load_font(FONT_SIZE_BUTTON)
        self.font = load_font(FONT_SIZE_SMALL + 4)
        self.background = load_cover_image("bg_img.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 160))
        self.back_btn = make_back_button(self.on_back)
        self.music_icon = make_music_icon()
        self.return_to = "mode_select"  # whoever opens this screen sets where Back goes

    def on_back(self) -> None:
        self.manager.switch(self.return_to)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        self.back_btn.handle_event(event)
        self.music_icon.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.background:
            surface.blit(self.background, (0, 0))
            surface.blit(self.overlay, (0, 0))
        else:
            surface.fill(BG_COLOR)
        heading = outlined_text(self.heading_font, "How to Play", HEADING_COLOR, outline=3)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        y = 116
        for title, lines in SECTIONS:
            surface.blit(outlined_text(self.section_font, title, HEADING_COLOR, outline=2), (140, y))
            y += 36
            for line in lines:
                surface.blit(outlined_text(self.font, line, TEXT_COLOR, outline=2), (170, y))
                y += 25
            y += 8
        self.back_btn.draw(surface)
        self.music_icon.draw(surface)
