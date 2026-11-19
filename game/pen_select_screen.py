"""Pen select screen: one big pen card on a wooden table. Use the arrows to flip through the six pens.

In Player vs Player each player picks in turn.
"""

import math
import random
from typing import Optional

import pygame

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    HEADING_COLOR,
    FONT_SIZE_BUTTON,
    FONT_SIZE_SMALL,
    AI_PLAYER_INDEX,
)
from common.pen import PEN_ORDER, PENS
from game import setup as game_setup
from game.assets import load_cover_image, load_font, load_image
from game.ai import PROFILES
from game.badge_button import BadgeButton, outlined_text
from game.common_ui import make_back_button, make_music_icon
from game.icon_button import IconButton
from game.music_icon import ICON_SIZE
from game.match import Match
from game.screen_manager import Screen

# Which picture shows each pen (files are in assets/images)
PEN_IMAGES = {
    "ball_pen": "Cheap_ballpoint.png",
    "gel_pen": "Gel_pen.png",
    "fountain_pen": "Fountain_pen.png",
    "marker": "Marker.png",
    "metal_pen": "Metal_pen.png",
    "highlighter": "Highlighter.png",
}

WOOD_FILE = "wood-bg.png"
NEXT_ICON_FILE = "play.png"
HEADING_SIZE = 56
HEADING_COLOR_WHITE = (255, 255, 255)

# Where the pen block (dots, picture, name) sits. The right side is left free.
CARD_RECT = pygame.Rect(150, 112, 560, 560)
CARD_BORDER_COLOR = (172, 162, 142)
PANEL_MARGIN = 18        # space between the card edge and the wooden picture panel
PANEL_TOP = 80           # the panel starts this far below the card top
PANEL_HEIGHT = 350
PANEL_RADIUS = 20
ARROW_SIZE = 64
ARROW_MARGIN = 14
PEN_FILL = (0.92, 0.92)  # the pen picture fills this share of the panel (width, height)

# Easy / Medium / Hard badges (Player vs Computer only), at the far right
BADGE_W, BADGE_H, BADGE_GAP = 300, 64, 18
BADGE_RIGHT_MARGIN = 40
BADGE_SELECTED_COLOR = (255, 215, 100)

DOT_COLOR = (112, 106, 98)
DOT_ACTIVE_COLOR = (228, 108, 40)
DOT_RADIUS = 5
DOT_GAP = 9
DOT_ACTIVE_WIDTH = 26


def _trim(image: pygame.Surface) -> pygame.Surface:
    """Cut away the empty transparent border around a picture."""
    mask = pygame.mask.from_surface(image, 128)  # ignore faint stray pixels
    rects = mask.get_bounding_rects()
    if not rects:
        return image
    return image.subsurface(rects[0].unionall(rects[1:])).copy()


def _fit_into(image: pygame.Surface, box: tuple) -> pygame.Surface:
    """Scale a picture up or down to fit inside box, keeping its shape."""
    scale = min(box[0] / image.get_width(), box[1] / image.get_height())
    size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
    return pygame.transform.smoothscale(image, size)


def _rounded(image: pygame.Surface, radius: int) -> pygame.Surface:
    """A copy of the picture with rounded corners."""
    result = image.convert_alpha()
    mask = pygame.Surface(result.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return result


def _make_background() -> Optional[pygame.Surface]:
    """The wooden table, darker towards the left and right edges. None if the picture is missing."""
    wood = load_cover_image(WOOD_FILE, (SCREEN_WIDTH, SCREEN_HEIGHT))
    if wood is None:
        return None
    shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    half = SCREEN_WIDTH / 2
    for x in range(SCREEN_WIDTH):
        edge = abs(x - half) / half
        pygame.draw.line(shade, (10, 8, 6, int(95 + 110 * edge * edge)), (x, 0), (x, SCREEN_HEIGHT))
    background = wood.copy()
    background.blit(shade, (0, 0))
    return background


class PenSelectScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.name_font = load_font(FONT_SIZE_BUTTON)
        self.small_font = load_font(FONT_SIZE_SMALL)
        self.heading_font = load_font(HEADING_SIZE)
        self.selected = PEN_ORDER[0]

        self.back_btn = make_back_button(self.on_back)
        self.music_icon = make_music_icon()
        self.next_btn = IconButton(
            NEXT_ICON_FILE, (SCREEN_WIDTH - 20 - ICON_SIZE, SCREEN_HEIGHT - 20 - ICON_SIZE), self.on_next
        )

        self.panel_rect = pygame.Rect(
            CARD_RECT.x + PANEL_MARGIN, CARD_RECT.y + PANEL_TOP,
            CARD_RECT.w - 2 * PANEL_MARGIN, PANEL_HEIGHT,
        )
        self.prev_btn = IconButton(
            "left.png", (self.panel_rect.x + ARROW_MARGIN, self.panel_rect.centery - ARROW_SIZE // 2),
            lambda: self.step(-1), ARROW_SIZE,
        )
        self.next_arrow = IconButton(
            "right.png", (self.panel_rect.right - ARROW_MARGIN - ARROW_SIZE, self.panel_rect.centery - ARROW_SIZE // 2),
            lambda: self.step(1), ARROW_SIZE,
        )

        self.background = _make_background()
        wood = load_cover_image(WOOD_FILE, self.panel_rect.size)
        self.panel_image = _rounded(wood, PANEL_RADIUS) if wood is not None else None
        self.pen_images = self._load_pen_images()

        self.difficulty_buttons = []
        total_h = 3 * BADGE_H + 2 * BADGE_GAP
        top = self.panel_rect.centery - total_h // 2
        x = SCREEN_WIDTH - BADGE_RIGHT_MARGIN - BADGE_W
        for i, key in enumerate(PROFILES):
            rect = (x, top + i * (BADGE_H + BADGE_GAP), BADGE_W, BADGE_H)
            self.difficulty_buttons.append(
                (key, BadgeButton(PROFILES[key].name, rect, lambda k=key: self.set_difficulty(k)))
            )

    def _load_pen_images(self) -> dict:
        """Every pen picture trimmed and scaled so all six pens have the same length on screen."""
        trimmed = {}
        for key, name in PEN_IMAGES.items():
            image = load_image(name)
            if image is not None:
                trimmed[key] = _trim(image)
        if not trimmed:
            return {}
        box_w, box_h = self.panel_rect.w * PEN_FILL[0], self.panel_rect.h * PEN_FILL[1]
        diagonals = []
        for image in trimmed.values():  # the longest diagonal that still fits the panel, for each pen
            w, h = image.get_size()
            diagonals.append(math.hypot(w, h) * min(box_w / w, box_h / h))
        target = min(diagonals)
        result = {}
        for key, image in trimmed.items():
            w, h = image.get_size()
            scale = target / math.hypot(w, h)
            result[key] = pygame.transform.smoothscale(image, (max(1, round(w * scale)), max(1, round(h * scale))))
        return result

    # ----- flow -----

    @property
    def _is_last_pick(self) -> bool:
        s = game_setup.setup
        return s.picking == s.picks_needed - 1

    def step(self, direction: int) -> None:
        """Show the next (+1) or the previous (-1) pen. After the last pen it starts again from the first."""
        index = (PEN_ORDER.index(self.selected) + direction) % len(PEN_ORDER)
        self.selected = PEN_ORDER[index]

    def set_difficulty(self, key: str) -> None:
        game_setup.setup.difficulty = key

    def on_enter(self) -> None:
        s = game_setup.setup
        self.selected = s.pens[s.picking]

    def on_back(self) -> None:
        s = game_setup.setup
        if s.picking > 0:  # go back to the previous pen
            s.picking -= 1
            self.on_enter()
        else:
            self.manager.switch("mode_select")

    def on_next(self) -> None:
        s = game_setup.setup
        s.pens[s.picking] = self.selected
        if not self._is_last_pick:
            s.picking += 1
            self.on_enter()
            return
        self._start_match()

    def _start_match(self) -> None:
        s = game_setup.setup
        pens = list(s.pens[: 2 * s.team_size])
        if s.mode == "pvc":
            pens[AI_PLAYER_INDEX] = random.choice(PEN_ORDER)  # the computer picks at random
        match = Match(
            pens,
            mode=s.mode,
            difficulty=s.difficulty if s.mode == "pvc" else None,
            team_size=s.team_size,
        )
        self.manager.get("match").start(match)
        self.manager.switch("match")

    # ----- events -----

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.on_back()
                return
            if event.key == pygame.K_LEFT:
                self.step(-1)
            elif event.key == pygame.K_RIGHT:
                self.step(1)
        self.prev_btn.handle_event(event)
        self.next_arrow.handle_event(event)
        self.back_btn.handle_event(event)
        self.music_icon.handle_event(event)
        self.next_btn.handle_event(event)
        if game_setup.setup.mode == "pvc":
            for _, button in self.difficulty_buttons:
                button.handle_event(event)

    # ----- drawing -----

    def _title(self) -> str:
        s = game_setup.setup
        player = s.picking_player + 1
        if s.mode == "team":
            slot = s.picking % s.team_size + 1
            return f"Pick your pen {slot} of {s.team_size}, Player {player}"
        if s.mode == "pvp":
            return f"Pick your pen, Player {player}"
        return "Pick your pen"

    def draw(self, surface: pygame.Surface) -> None:
        if self.background is not None:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(BG_COLOR)
        s = game_setup.setup

        heading = outlined_text(self.heading_font, self._title(), HEADING_COLOR_WHITE, outline=3)
        surface.blit(heading, heading.get_rect(center=(SCREEN_WIDTH // 2, 48)))

        if s.mode == "team" and s.picking % s.team_size > 0:  # the team picked so far
            first = s.picking_player * s.team_size
            chosen = ", ".join(PENS[k].name for k in s.pens[first:s.picking])
            line = self.small_font.render(f"Your team so far: {chosen}", True, TEXT_COLOR)
            surface.blit(line, line.get_rect(center=(SCREEN_WIDTH // 2, 92)))

        self._draw_card(surface)
        if s.mode == "pvc":
            self._draw_difficulty(surface)

        self.back_btn.draw(surface)
        self.music_icon.draw(surface)
        self.next_btn.draw(surface)

    def _draw_card(self, surface: pygame.Surface) -> None:
        stats = PENS[self.selected]

        self._draw_dots(surface)

        # Wooden panel with the pen on it
        if self.panel_image is not None:
            surface.blit(self.panel_image, self.panel_rect)
        else:
            pygame.draw.rect(surface, (96, 66, 44), self.panel_rect, border_radius=PANEL_RADIUS)
        pygame.draw.rect(surface, CARD_BORDER_COLOR, self.panel_rect, width=3, border_radius=PANEL_RADIUS)

        image = self.pen_images.get(self.selected)
        if image is not None:
            surface.blit(image, image.get_rect(center=self.panel_rect.center))
        else:  # picture missing: a plain coloured bar so the screen still works
            bar = pygame.Rect(0, 0, int(stats.length * 1.6), int(stats.width * 1.6))
            bar.center = self.panel_rect.center
            pygame.draw.rect(surface, stats.color, bar, border_radius=8)

        self.prev_btn.draw(surface)
        self.next_arrow.draw(surface)

        name = outlined_text(self.name_font, stats.name, TEXT_COLOR)
        surface.blit(name, name.get_rect(center=(CARD_RECT.centerx, self.panel_rect.bottom + 38)))
        desc = outlined_text(self.small_font, stats.description, (235, 228, 214), outline=2)
        surface.blit(desc, desc.get_rect(center=(CARD_RECT.centerx, self.panel_rect.bottom + 78)))

    def _draw_dots(self, surface: pygame.Surface) -> None:
        """One dot per pen; the current pen is a longer orange one."""
        current = PEN_ORDER.index(self.selected)
        widths = [DOT_ACTIVE_WIDTH if i == current else 2 * DOT_RADIUS for i in range(len(PEN_ORDER))]
        x = CARD_RECT.centerx - (sum(widths) + DOT_GAP * (len(widths) - 1)) // 2
        y = CARD_RECT.y + 40
        for i, width in enumerate(widths):
            rect = pygame.Rect(x, y - DOT_RADIUS, width, 2 * DOT_RADIUS)
            color = DOT_ACTIVE_COLOR if i == current else DOT_COLOR
            pygame.draw.rect(surface, color, rect, border_radius=DOT_RADIUS)
            x += width + DOT_GAP

    def _draw_difficulty(self, surface: pygame.Surface) -> None:
        """COMPUTER label and the Easy / Medium / Hard badges; the chosen one gets a yellow frame."""
        first = self.difficulty_buttons[0][1].rect
        label = outlined_text(self.small_font, "COMPUTER", HEADING_COLOR, outline=2)
        surface.blit(label, label.get_rect(midbottom=(first.centerx, first.y - 16)))
        for key, button in self.difficulty_buttons:
            if key == game_setup.setup.difficulty:
                pygame.draw.rect(surface, BADGE_SELECTED_COLOR, button.rect.inflate(16, 14), width=4, border_radius=16)
            button.draw(surface)