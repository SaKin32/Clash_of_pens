"""Match screen: draws a Match and turns mouse input into flicks.

The rules live in game/match.py and the computer player in game/ai.py. This file
only shows the match, reads the mouse, pauses, and saves.
"""

import math
import random
from typing import Optional

import pygame
import pymunk

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    BOARD_COLOR,
    BOARD_BORDER_COLOR,
    PEN_OUTLINE_COLOR,
    PHYSICS_DAMPING,
    FONT_SIZE_SMALL,
    FONT_SIZE_BUTTON,
    FONT_SIZE_HEADING,
    GRAB_MARGIN,
    MAX_PULL_DISTANCE,
    MIN_PULL_DISTANCE,
    MAX_SHOT_SPEED,
    POWER_CURVE,
    AIM_LINE_COLOR,
    PULL_LINE_COLOR,
    TURN_RING_COLOR,
    POWER_BAR_RECT,
    POWER_BAR_BG_COLOR,
    BOARD_RECT,
    WARNING_COLOR,
    WOBBLE_ZONE,
    WOBBLE_AMOUNT,
    FALL_DURATION,
    FALL_BANNER_COLOR,
    TURN_TIME_LIMIT,
    TIMER_WARNING_TIME,
    TIMER_BAR_RECT,
    PAUSE_OVERLAY_COLOR,
    PAUSE_BUTTON_WIDTH,
    BUTTON_HEIGHT,
    BUTTON_GAP,
    AI_THINK_TIME,
    AI_PLAYER_INDEX,
)
from common.pen import get_pen
from game import save, settings
from game.ai import AIPlayer
from game.assets import load_image
from game.button import Button
from game.match import Match, PLAYER_COLORS
from game.physics import Pen, PenWorld
from game.screen_manager import Screen


def predicted_distance(speed: float) -> float:
    """Distance a pen travels before stopping, given its launch speed.

    pymunk damping multiplies velocity by DAMPING each second, so
    v(t) = v0 * DAMPING**t and the total distance is v0 * (1 - DAMPING) / -ln(DAMPING).
    Collisions and spin are not included, so this is a guide only.
    """
    return speed * (1 - PHYSICS_DAMPING) / -math.log(PHYSICS_DAMPING)


class MatchScreen(Screen):
    """A match on one computer: two players, or one player against the computer."""

    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.big_font = pygame.font.Font(None, FONT_SIZE_BUTTON)
        self.huge_font = pygame.font.Font(None, FONT_SIZE_HEADING)

        self.match = Match()
        self.ai: Optional[AIPlayer] = None
        self.paused = False
        self.dragging = False
        self.grab_local = pymunk.Vec2d(0, 0)
        self._turn_id = -1       # used to notice that a new turn began
        self._ai_wait = 0.0      # seconds left before the computer flicks
        self._save_cleared = False

        self.pause_buttons = [
            Button("Resume", self._pause_rect(0), self.on_resume),
            Button("", self._pause_rect(1), self.on_toggle_music),
            Button("How to Play", self._pause_rect(2), self.on_how_to_play),
            Button("Save & Exit to Menu", self._pause_rect(3), self.on_save_and_exit),
        ]
        self.music_btn = self.pause_buttons[1]

    # ----- starting a match -----

    def start(self, match: Match) -> None:
        """Begin playing the given match (called by the pen select screen and Resume)."""
        self.match = match
        self.ai = None
        if match.mode == "pvc":
            self.ai = AIPlayer(match.difficulty or "medium")
        self.paused = False
        self.dragging = False
        self._turn_id = -1
        self._save_cleared = False

    def resume_from_save(self, state: dict) -> None:
        self.start(Match.from_state(state))

    # ----- pause menu -----

    @staticmethod
    def _pause_rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - PAUSE_BUTTON_WIDTH) // 2
        y = 240 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, PAUSE_BUTTON_WIDTH, BUTTON_HEIGHT)

    def _update_music_label(self) -> None:
        self.music_btn.text = "Music: On" if settings.is_music_on() else "Music: Off"

    def on_enter(self) -> None:
        self._update_music_label()

    def on_resume(self) -> None:
        self.paused = False

    def on_toggle_music(self) -> None:
        settings.set_music_on(not settings.is_music_on())
        self._update_music_label()

    def on_how_to_play(self) -> None:
        screen = self.manager.get("how_to_play")
        screen.return_to = "match"  # Back returns here, with the match still paused
        self.manager.switch("how_to_play")

    def on_save_and_exit(self) -> None:
        self._save_match()
        self.manager.switch("title")

    def _save_match(self) -> None:
        if self.match.match_winner is None:
            save.save_game(self.match.to_state())

    def on_quit(self) -> None:
        """The window is closing: keep the match so Resume can continue it."""
        self._save_match()

    # ----- helpers -----

    @property
    def active_pen(self) -> Pen:
        return self.match.active_pen

    @property
    def _human_turn(self) -> bool:
        return self.ai is None or self.match.current != AI_PLAYER_INDEX

    def _grab_world(self) -> pymunk.Vec2d:
        return self.active_pen.body.local_to_world(self.grab_local)

    def _pull_vector(self, mouse_pos: tuple) -> pymunk.Vec2d:
        pull = self._grab_world() - pymunk.Vec2d(*mouse_pos)
        if pull.length > MAX_PULL_DISTANCE:
            pull = pull.normalized() * MAX_PULL_DISTANCE
        return pull

    @staticmethod
    def _power(pull: pymunk.Vec2d) -> float:
        return (pull.length / MAX_PULL_DISTANCE) ** POWER_CURVE

    def _grabbed(self, mouse_pos: tuple) -> bool:
        info = self.active_pen.shape.point_query(mouse_pos)
        return info.distance <= GRAB_MARGIN

    def _fire(self, mouse_pos: tuple) -> None:
        pull = self._pull_vector(mouse_pos)
        if pull.length < MIN_PULL_DISTANCE:
            return
        self.match.shoot(pull, self._power(pull), self.grab_local)

    def _player_label(self, index: int) -> str:
        if self.ai is not None and index == AI_PLAYER_INDEX:
            return "Computer"
        return f"Player {index + 1}"

    # ----- events -----

    def handle_event(self, event: pygame.event.Event) -> None:
        m = self.match
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if m.match_winner is not None:
                    self.manager.switch("mode_select")
                else:
                    self.paused = not self.paused
                    self.dragging = False
                    self._update_music_label()
                return
            if not self.paused and m.round_over:
                if m.match_winner is not None:
                    if event.key == pygame.K_r:
                        m.reset_match()
                        self.dragging = False
                        self._turn_id = -1
                        self._save_cleared = False
                elif event.key in (pygame.K_r, pygame.K_SPACE):
                    if m.next_round():
                        self.dragging = False
                        self._turn_id = -1
                return

        if self.paused:
            for button in self.pause_buttons:
                button.handle_event(event)
            return

        if not m.can_shoot or not self._human_turn:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._grabbed(event.pos):
                self.grab_local = self.active_pen.body.world_to_local(event.pos)
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                self._fire(event.pos)

    # ----- update -----

    def update(self, dt: float) -> None:
        if self.paused:
            return
        m = self.match
        m.step(dt)

        if m.turn_id != self._turn_id:  # a new turn started (or a skipped one)
            self._turn_id = m.turn_id
            self.dragging = False
            self._ai_wait = random.uniform(*AI_THINK_TIME)
        if not m.can_shoot:
            self.dragging = False

        if self.ai is not None and m.can_shoot and m.current == AI_PLAYER_INDEX:
            self._ai_wait -= dt
            if self._ai_wait <= 0:
                shot = self.ai.choose_shot(m)
                m.shoot(shot.direction, shot.power)

        # A finished match cannot be resumed, so remove its save
        if m.match_winner is not None and not self._save_cleared:
            save.delete_save()
            self._save_cleared = True

    # ----- drawing -----

    def draw(self, surface: pygame.Surface) -> None:
        m = self.match
        bg = load_image("match_bg.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        if bg:
            surface.blit(bg, (0, 0))
        else:
            surface.fill(BG_COLOR)
        self._draw_board(surface)

        for i, pen in enumerate(m.world.pens):
            self._draw_pen(surface, i, pen)

        if not m.round_over:
            self._draw_turn_indicator(surface)
        if self.dragging:
            self._draw_aim(surface)
        self._draw_power_bar(surface)
        self._draw_warning_text(surface)
        self._draw_score(surface)
        self._draw_timer(surface)
        self._draw_pen_names(surface)
        self._draw_round_over(surface)

        hint = self.font.render(
            "Grab your pen anywhere, pull back, release to flick    ESC: pause",
            True,
            TEXT_COLOR,
        )
        surface.blit(hint, hint.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)))

        if self.paused:
            self._draw_pause(surface)

    def _draw_board(self, surface: pygame.Surface) -> None:
        m = self.match
        # Dark table area under the board so shrinking is visible
        full = pygame.Rect(BOARD_RECT)
        pygame.draw.rect(surface, (22, 25, 33), full)
        pygame.draw.rect(surface, (45, 50, 62), full, width=2)

        board = pygame.Rect(m.board.as_tuple())
        texture = load_image("board.png")
        if texture and board.width > 0 and board.height > 0:
            surface.blit(pygame.transform.scale(texture, board.size), board)
        else:
            pygame.draw.rect(surface, BOARD_COLOR, board)
        pygame.draw.rect(surface, BOARD_BORDER_COLOR, board, width=6)

        # Warning box: dashed red rectangle that flashes
        if m.board.target is not None and not m.board.shrinking:
            if int(pygame.time.get_ticks() / 300) % 2 == 0:
                self._draw_dashed_rect(surface, pygame.Rect(m.board.target))

    @staticmethod
    def _draw_dashed_rect(surface: pygame.Surface, rect: pygame.Rect) -> None:
        dash, gap = 16, 10
        x1, y1, x2, y2 = rect.left, rect.top, rect.right, rect.bottom
        for x in range(x1, x2, dash + gap):
            pygame.draw.line(surface, WARNING_COLOR, (x, y1), (min(x + dash, x2), y1), 4)
            pygame.draw.line(surface, WARNING_COLOR, (x, y2), (min(x + dash, x2), y2), 4)
        for y in range(y1, y2, dash + gap):
            pygame.draw.line(surface, WARNING_COLOR, (x1, y), (x1, min(y + dash, y2)), 4)
            pygame.draw.line(surface, WARNING_COLOR, (x2, y), (x2, min(y + dash, y2)), 4)

    def _draw_pen(self, surface: pygame.Surface, index: int, pen: Pen) -> None:
        m = self.match
        corners = pen.corners()
        center = pen.body.position
        offset = pymunk.Vec2d(0, 0)
        scale = 1.0
        fade = 0.0
        body_color = pen.stats.color if pen.stats else pen.color
        outline_color = pen.color  # the player's colour, so you can tell the pens apart

        if index in m.falling:
            # Tip over: shrink toward the center and fade
            t = min(1.0, m.falling[index] / FALL_DURATION)
            if t >= 1.0:
                return
            scale = 1.0 - 0.85 * t
            fade = 0.6 * t
            corners = [center + (c - center) * scale for c in corners]
            body_color = tuple(int(c * (1 - fade)) for c in body_color)
            outline_color = tuple(int(c * (1 - fade)) for c in outline_color)
        else:
            # Wobble when the center is close to the edge
            dist = PenWorld.edge_distance(pen, m.board.as_tuple())
            if 0 <= dist < WOBBLE_ZONE and not m.round_over:
                amount = WOBBLE_AMOUNT * (1 - dist / WOBBLE_ZONE)
                offset = pymunk.Vec2d(
                    random.uniform(-amount, amount), random.uniform(-amount, amount)
                )
                corners = [c + offset for c in corners]

        key = pen.stats.key if pen.stats else f"p{index + 1}"
        image = load_image(f"pen_{key}.png", (pen.length, pen.width))
        if image:
            if scale < 1.0:
                size = (max(1, int(pen.length * scale)), max(1, int(pen.width * scale)))
                image = pygame.transform.smoothscale(image, size)
            # pymunk angles turn clockwise on screen (y points down), pygame rotates counter-clockwise
            image = pygame.transform.rotate(image, -math.degrees(pen.body.angle))
            if fade:
                image.set_alpha(int(255 * (1 - fade)))
            pos = center + offset
            surface.blit(image, image.get_rect(center=(pos.x, pos.y)))
            return

        pygame.draw.polygon(surface, body_color, corners)
        pygame.draw.polygon(surface, outline_color, corners, width=4)

    def _draw_turn_indicator(self, surface: pygame.Surface) -> None:
        m = self.match
        pen = self.active_pen
        if m.can_shoot:
            c = (int(pen.body.position.x), int(pen.body.position.y))
            pygame.draw.circle(surface, TURN_RING_COLOR, c, 18, width=2)
        label = f"{self._player_label(m.current)}'s turn"
        if self.ai is not None and m.current == AI_PLAYER_INDEX and m.can_shoot:
            label = "Computer is thinking..."
        text = self.big_font.render(label, True, PLAYER_COLORS[m.current])
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 60)))

        counts = self.font.render(
            f"Turn {m.turns_taken[m.current] + 1} of {m.turn_limit}"
            f"    Shots  P1: {m.shots[0]}   P2: {m.shots[1]}",
            True,
            TEXT_COLOR,
        )
        surface.blit(counts, counts.get_rect(center=(SCREEN_WIDTH // 2, 90)))

    def _draw_pen_names(self, surface: pygame.Surface) -> None:
        m = self.match
        for i, x in ((0, 200), (1, SCREEN_WIDTH - 200)):
            name = get_pen(m.pen_keys[i]).name
            text = self.font.render(f"{self._player_label(i)}: {name}", True, PLAYER_COLORS[i])
            rect = text.get_rect(midleft=(x, 60)) if i == 0 else text.get_rect(midright=(x, 60))
            surface.blit(text, rect)

    def _draw_warning_text(self, surface: pygame.Surface) -> None:
        m = self.match
        if m.board.target is not None and not m.board.shrinking:
            text = self.big_font.render(
                "WARNING: board shrinks next turn!", True, WARNING_COLOR
            )
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 640 - 40)))
        elif m.sudden_death and not m.round_over:
            text = self.big_font.render("SUDDEN DEATH", True, WARNING_COLOR)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 640 - 40)))

    def _draw_score(self, surface: pygame.Surface) -> None:
        m = self.match
        label = f"P1  {m.scores[0]} - {m.scores[1]}  P2    Round {m.round_number}"
        if self.ai is not None:
            label = f"You  {m.scores[0]} - {m.scores[1]}  CPU    Round {m.round_number}"
        text = self.big_font.render(label, True, TEXT_COLOR)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 25)))

    def _draw_round_over(self, surface: pygame.Surface) -> None:
        m = self.match
        if not m.round_over or not m.round_result_applied:
            return

        if m.match_winner is not None:
            msg = f"{self._player_label(m.match_winner)} wins the match!"
            sub_text = "Press R for a new match    ESC: menu"
        else:
            if m.last_result == "draw_replay":
                msg = "Draw! Replaying the round"
            elif m.last_result == "sudden_death":
                msg = "Draw again! SUDDEN DEATH next"
            elif m.last_result == "draw_decided":
                msg = f"Draw: {self._player_label(m.round_winner)} wins (closer to the middle)"
            else:
                msg = f"{self._player_label(m.round_winner)} wins the round!"
            sub_text = "Press SPACE for the next round"

        text = self.huge_font.render(msg, True, FALL_BANNER_COLOR)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        sub = self.big_font.render(sub_text, True, TEXT_COLOR)
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 56)))

    def _draw_aim(self, surface: pygame.Surface) -> None:
        pull = self._pull_vector(pygame.mouse.get_pos())
        if pull.length < MIN_PULL_DISTANCE:
            return
        start = self._grab_world()
        pygame.draw.line(surface, PULL_LINE_COLOR, start, start - pull, 3)
        pygame.draw.circle(surface, PULL_LINE_COLOR, (int(start.x), int(start.y)), 5)

        speed = self._power(pull) * MAX_SHOT_SPEED * self.active_pen.power
        distance = predicted_distance(speed)
        direction = pull.normalized()
        step = 18
        for d in range(step, int(distance), step):
            dot = start + direction * d
            pygame.draw.circle(surface, AIM_LINE_COLOR, (int(dot.x), int(dot.y)), 3)

    def _draw_power_bar(self, surface: pygame.Surface) -> None:
        bar = pygame.Rect(POWER_BAR_RECT)
        pygame.draw.rect(surface, POWER_BAR_BG_COLOR, bar, border_radius=6)

        power = 0.0
        if self.dragging:
            power = self._power(self._pull_vector(pygame.mouse.get_pos()))

        if power > 0:
            fill = bar.copy()
            fill.width = int(bar.width * power)
            color = (int(60 + 195 * power), int(220 - 150 * power), 70)
            pygame.draw.rect(surface, color, fill, border_radius=6)
        pygame.draw.rect(surface, TEXT_COLOR, bar, width=2, border_radius=6)

    def _draw_timer(self, surface: pygame.Surface) -> None:
        m = self.match
        if m.round_over:
            return
        seconds = max(0, int(m.turn_time_left) + 1)
        urgent = m.turn_time_left <= TIMER_WARNING_TIME
        color = WARNING_COLOR if urgent else TEXT_COLOR
        text = self.big_font.render(f"{seconds}", True, color)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH - 90, 100)))

        # Thin bar under the power bar showing the time left
        bar = pygame.Rect(TIMER_BAR_RECT)
        pygame.draw.rect(surface, POWER_BAR_BG_COLOR, bar, border_radius=5)
        ratio = max(0.0, m.turn_time_left / TURN_TIME_LIMIT)
        if ratio > 0:
            fill = bar.copy()
            fill.width = int(bar.width * ratio)
            pygame.draw.rect(surface, color, fill, border_radius=5)

    def _draw_pause(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(PAUSE_OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))
        title = self.huge_font.render("Paused", True, FALL_BANNER_COLOR)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 160)))
        for button in self.pause_buttons:
            button.draw(surface)
