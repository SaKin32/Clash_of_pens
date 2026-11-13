"""Pen select screen: pick one of the six pens. In Player vs Player each player picks in turn."""

import random

import pygame

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
    BACK_BUTTON_RECT,
    CARD_COLOR,
    CARD_HOVER_COLOR,
    CARD_SELECTED_BORDER_COLOR,
    STAT_BAR_BG_COLOR,
    STAT_BAR_FILL_COLOR,
    PEN_OUTLINE_COLOR,
    AI_PLAYER_INDEX,
)
from common.pen import PEN_ORDER, PENS
from game import setup as game_setup
from game.button import Button
from game.match import Match, PLAYER_COLORS
from game.screen_manager import Screen

CARD_W, CARD_H = 360, 210
CARD_GAP_X, CARD_GAP_Y = 30, 22
CARD_TOP = 130

# (label, how to read the stat from a pen, lowest value, highest value) for the bars
STAT_BARS = (
    ("Weight", lambda s: s.mass, 1.5, 4.5),
    ("Power", lambda s: s.power, 0.8, 1.2),
    ("Length", lambda s: s.length, 120, 210),
    ("Bounce", lambda s: s.elasticity, 0.4, 0.75),
)


class PenSelectScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.heading_font = pygame.font.Font(None, 56)
        self.name_font = pygame.font.Font(None, FONT_SIZE_BUTTON)
        self.small_font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.selected = PEN_ORDER[0]
        self.back_btn = Button("Back", BACK_BUTTON_RECT, self.on_back)
        self.next_btn = Button(
            "Next", (SCREEN_WIDTH - 24 - 200, SCREEN_HEIGHT - 84, 200, 56), self.on_next
        )

    def _card_rect(self, index: int) -> pygame.Rect:
        col, row = index % 3, index // 3
        total_w = 3 * CARD_W + 2 * CARD_GAP_X
        x = (SCREEN_WIDTH - total_w) // 2 + col * (CARD_W + CARD_GAP_X)
        y = CARD_TOP + row * (CARD_H + CARD_GAP_Y)
        return pygame.Rect(x, y, CARD_W, CARD_H)

    # ----- flow -----

    @property
    def _is_last_pick(self) -> bool:
        s = game_setup.setup
        return s.mode == "pvc" or s.picking == 1

    def on_enter(self) -> None:
        s = game_setup.setup
        self.selected = s.pens[s.picking]
        self.next_btn.text = "Play!" if self._is_last_pick else "Next"

    def on_back(self) -> None:
        s = game_setup.setup
        if s.mode == "pvp" and s.picking == 1:
            s.picking = 0
            self.on_enter()
        elif s.mode == "pvc":
            self.manager.switch("difficulty_select")
        else:
            self.manager.switch("mode_select")

    def on_next(self) -> None:
        s = game_setup.setup
        s.pens[s.picking] = self.selected
        if s.mode == "pvp" and s.picking == 0:
            s.picking = 1
            self.on_enter()
            return
        self._start_match()

    def _start_match(self) -> None:
        s = game_setup.setup
        pens = list(s.pens)
        if s.mode == "pvc":
            pens[AI_PLAYER_INDEX] = random.choice(PEN_ORDER)  # the computer picks at random
        match = Match(pens, mode=s.mode, difficulty=s.difficulty if s.mode == "pvc" else None)
        self.manager.get("match").start(match)
        self.manager.switch("match")

    # ----- events -----

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, key in enumerate(PEN_ORDER):
                if self._card_rect(i).collidepoint(event.pos):
                    self.selected = key
        self.back_btn.handle_event(event)
        self.next_btn.handle_event(event)

    # ----- drawing -----

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        s = game_setup.setup
        if s.mode == "pvp":
            title = f"Player {s.picking + 1}: choose your pen"
            color = PLAYER_COLORS[s.picking]
        else:
            title, color = "Choose your pen", HEADING_COLOR
        heading = self.heading_font.render(title, True, color)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        mouse = pygame.mouse.get_pos()
        for i, key in enumerate(PEN_ORDER):
            self._draw_card(surface, self._card_rect(i), PENS[key], key == self.selected, mouse)

        self.back_btn.draw(surface)
        self.next_btn.draw(surface)

    def _draw_card(self, surface, rect: pygame.Rect, stats, selected: bool, mouse) -> None:
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(surface, CARD_HOVER_COLOR if hovered else CARD_COLOR, rect, border_radius=12)
        if selected:
            pygame.draw.rect(surface, CARD_SELECTED_BORDER_COLOR, rect, width=4, border_radius=12)

        name = self.name_font.render(stats.name, True, TEXT_COLOR)
        surface.blit(name, (rect.x + 16, rect.y + 12))
        desc = self.small_font.render(stats.description, True, TEXT_COLOR)
        surface.blit(desc, (rect.x + 16, rect.y + 44))

        # Small picture of the pen, drawn to scale with its real length and width
        pen_rect = pygame.Rect(0, 0, int(stats.length * 0.5), int(stats.width * 0.5))
        pen_rect.midright = (rect.right - 16, rect.y + 24)
        pygame.draw.rect(surface, stats.color, pen_rect, border_radius=4)
        pygame.draw.rect(surface, PEN_OUTLINE_COLOR, pen_rect, width=2, border_radius=4)

        for n, (label, read, low, high) in enumerate(STAT_BARS):
            y = rect.y + 80 + n * 30
            text = self.small_font.render(label, True, TEXT_COLOR)
            surface.blit(text, (rect.x + 16, y))
            bar = pygame.Rect(rect.x + 110, y + 3, 220, 14)
            pygame.draw.rect(surface, STAT_BAR_BG_COLOR, bar, border_radius=5)
            fraction = max(0.08, min(1.0, (read(stats) - low) / (high - low)))
            fill = bar.copy()
            fill.width = int(bar.width * fraction)
            pygame.draw.rect(surface, STAT_BAR_FILL_COLOR, fill, border_radius=5)
