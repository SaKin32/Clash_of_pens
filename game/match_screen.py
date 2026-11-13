"""Match screen: shrinking board, flick-to-shoot, wobble, falling pens, best of 3."""

import math
import random

import pygame
import pymunk

from common.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    TEXT_COLOR,
    BOARD_COLOR,
    BOARD_BORDER_COLOR,
    PEN_COLOR_P1,
    PEN_COLOR_P2,
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
    MAX_SPIN,
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
    ROUNDS_TO_WIN,
    MAX_DRAW_REPLAYS,
    TURN_TIME_LIMIT,
    TIMER_WARNING_TIME,
    TIMER_BAR_RECT,
    PEN_LENGTH,
    PEN_WIDTH,
)
from game.board import Board
from game.physics import Pen, PenWorld
from game.screen_manager import Screen
from game.assets import load_image


def predicted_distance(speed: float) -> float:
    """Distance a pen travels before stopping, given its launch speed.

    pymunk damping multiplies velocity by DAMPING each second, so
    v(t) = v0 * DAMPING**t and the total distance is v0 * (1 - DAMPING) / -ln(DAMPING).
    Collisions and spin are not included, so this is a guide only.
    """
    return speed * (1 - PHYSICS_DAMPING) / -math.log(PHYSICS_DAMPING)


class MatchScreen(Screen):
    """Local match: players take turns flicking their own pen."""

    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.big_font = pygame.font.Font(None, FONT_SIZE_BUTTON)
        self.huge_font = pygame.font.Font(None, FONT_SIZE_HEADING)
        self.round_over = False
        self.draw_by_limit = False
        self.round_result_applied = False
        self.world = PenWorld()
        self.board = Board()
        self.reset_match()

    def on_enter(self) -> None:
        self.reset_match()

    def reset_match(self) -> None:
        """Start a brand new match: scores back to 0-0."""
        self.scores = [0, 0]
        self.draw_replays_used = 0
        self.round_number = 1
        self.match_winner = None  # 0 or 1 once someone wins the match
        self.last_result = ""
        self.reset_round()

    def reset_round(self) -> None:
        """Start a fresh board with both pens in place."""
        self.world = PenWorld()
        self.board = Board()
        x, y, w, h = BOARD_RECT
        cy = y + h / 2
        self.world.add_pen((x + 220, cy), 0.0, PEN_COLOR_P1)
        self.world.add_pen((x + w - 220, cy), math.pi, PEN_COLOR_P2)
        self.current = 0
        self.dragging = False
        self.grab_local = pymunk.Vec2d(0, 0)
        self.shot_in_flight = False
        self.shots = [0, 0]  # shots taken by each player
        self.falling = {}  # pen index -> seconds since it started falling
        self.fallen = []  # pen indices that have fully fallen
        self.round_over = False
        self.draw_by_limit = False  # draw because the board cannot shrink more
        self.round_result_applied = False
        self.round_winner = None  # 0 or 1, or None for a replayed draw
        self.turn_time_left = TURN_TIME_LIMIT
        self.turns_taken = [0, 0]  # turns used by each player, including skipped ones

    # ----- helpers -----

    @property
    def active_pen(self) -> Pen:
        return self.world.pens[self.current]

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
        speed = self._power(pull) * MAX_SHOT_SPEED
        body = self.active_pen.body
        impulse = pull.normalized() * (speed * body.mass)
        body.apply_impulse_at_world_point(impulse, self._grab_world())
        body.angular_velocity = max(-MAX_SPIN, min(MAX_SPIN, body.angular_velocity))
        self.shot_in_flight = True
        self.shots[self.current] += 1
        self.turns_taken[self.current] += 1

    # ----- events -----

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.switch("mode_select")
                return
            if event.key in (pygame.K_r, pygame.K_SPACE) and self.round_over:
                if self.match_winner is not None:
                    if event.key == pygame.K_r:
                        self.reset_match()
                elif self.round_result_applied:
                    self.reset_round()
                return

        if self.round_over or self.shot_in_flight or self.board.shrinking:
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
        self.world.step(dt)
        self.board.update(dt)
        self._update_falling(dt)

        if self.round_over:
            self._apply_round_result()
            return

        # Timer runs only while the active player is choosing a shot
        if not self.shot_in_flight and not self.board.shrinking:
            self.turn_time_left -= dt
            if self.turn_time_left <= 0:
                self._skip_turn()
                return

        if self.shot_in_flight and self.world.is_settled():
            self.world.stop_all()
            self.shot_in_flight = False
            self._end_turn()

    def _skip_turn(self) -> None:
        """Time ran out: the move is lost and the turn passes on."""
        self.dragging = False
        self.turns_taken[self.current] += 1
        self._end_turn()

    def _update_falling(self, dt: float) -> None:
        """Detect pens whose center left the board and animate their fall."""
        board = self.board.as_tuple()
        for i, pen in enumerate(self.world.pens):
            if i in self.falling:
                self.falling[i] += dt
                if self.falling[i] >= FALL_DURATION and i not in self.fallen:
                    self.fallen.append(i)
            elif PenWorld.edge_distance(pen, board) < 0:
                self.falling[i] = 0.0

        if self.falling and not self.round_over:
            self.round_over = True
            self.dragging = False

    def _end_turn(self) -> None:
        # A fallen pen ends the round, no more turns
        if self.falling:
            return
        self.current = 1 - self.current
        self.turn_time_left = TURN_TIME_LIMIT
        # Both players have used a turn: check shrink warning or final draw
        if self.current == 0:
            self.board.on_turn_completed(self.turns_taken[0])
            if self.board.maxed and self.turns_taken[0] >= self.board.next_event_turn:
                self.draw_by_limit = True
                self.round_over = True
                self.dragging = False
                return
        self.board.on_next_turn_started()

    def _round_winner(self):
        """Return 0 or 1 for the round winner, or None for a draw."""
        if self.draw_by_limit:
            return None
        if len(self.fallen) >= 2:
            return None
        if len(self.fallen) == 1:
            return 1 - self.fallen[0]
        return None

    def _apply_round_result(self) -> None:
        """Work out who won the round (once), update scores and match state."""
        if self.round_result_applied:
            return
        # Wait for the fall animation before deciding
        if not self.draw_by_limit and not self.fallen:
            return
        self.round_result_applied = True

        winner = self._round_winner()
        if winner is not None:
            self.last_result = "win"
        elif self.draw_replays_used < MAX_DRAW_REPLAYS:
            # First draw of the match: replay the round
            self.draw_replays_used += 1
            self.last_result = "draw_replay"
        else:
            # Another draw: the pen further inside the board wins
            board = self.board.as_tuple()
            d0 = PenWorld.edge_distance(self.world.pens[0], board)
            d1 = PenWorld.edge_distance(self.world.pens[1], board)
            winner = 0 if d0 >= d1 else 1
            self.last_result = "draw_decided"

        self.round_winner = winner
        if winner is not None:
            self.scores[winner] += 1
            self.round_number += 1
            if self.scores[winner] >= ROUNDS_TO_WIN:
                self.match_winner = winner

    # ----- drawing -----

    def draw(self, surface: pygame.Surface) -> None:
        bg = load_image("match_bg.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        if bg:
            surface.blit(bg, (0, 0))
        else:
            surface.fill(BG_COLOR)
        self._draw_board(surface)

        for i, pen in enumerate(self.world.pens):
            self._draw_pen(surface, i, pen)

        if not self.round_over:
            self._draw_turn_indicator(surface)
        if self.dragging:
            self._draw_aim(surface)
        self._draw_power_bar(surface)
        self._draw_warning_text(surface)
        self._draw_score(surface)
        self._draw_timer(surface)
        self._draw_round_over(surface)

        hint = self.font.render(
            "Grab your pen anywhere, pull back, release to flick    ESC: back",
            True,
            TEXT_COLOR,
        )
        surface.blit(hint, hint.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10)))

    def _draw_board(self, surface: pygame.Surface) -> None:
        # Dark table area under the board so shrinking is visible
        full = pygame.Rect(BOARD_RECT)
        pygame.draw.rect(surface, (22, 25, 33), full)
        pygame.draw.rect(surface, (45, 50, 62), full, width=2)

        board = pygame.Rect(self.board.as_tuple())
        texture = load_image("board.png")
        if texture and board.width > 0 and board.height > 0:
            surface.blit(pygame.transform.scale(texture, board.size), board)
        else:
            pygame.draw.rect(surface, BOARD_COLOR, board)
        pygame.draw.rect(surface, BOARD_BORDER_COLOR, board, width=6)

        # Warning box: dashed red rectangle that flashes
        if self.board.target is not None and not self.board.shrinking:
            if int(pygame.time.get_ticks() / 300) % 2 == 0:
                self._draw_dashed_rect(surface, pygame.Rect(self.board.target))

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
        corners = pen.corners()
        center = pen.body.position
        offset = pymunk.Vec2d(0, 0)
        scale = 1.0
        fade = 0.0

        if index in self.falling:
            # Tip over: shrink toward the center and fade
            t = min(1.0, self.falling[index] / FALL_DURATION)
            if t >= 1.0:
                return
            scale = 1.0 - 0.85 * t
            fade = 0.6 * t
            corners = [center + (c - center) * scale for c in corners]
            color = tuple(int(c * (1 - fade)) for c in pen.color)
        else:
            color = pen.color
            # Wobble when the center is close to the edge
            dist = PenWorld.edge_distance(pen, self.board.as_tuple())
            if 0 <= dist < WOBBLE_ZONE and not self.round_over:
                amount = WOBBLE_AMOUNT * (1 - dist / WOBBLE_ZONE)
                offset = pymunk.Vec2d(
                    random.uniform(-amount, amount), random.uniform(-amount, amount)
                )
                corners = [c + offset for c in corners]

        image = load_image(f"pen_p{index + 1}.png", (PEN_LENGTH, PEN_WIDTH))
        if image:
            if scale < 1.0:
                size = (max(1, int(PEN_LENGTH * scale)), max(1, int(PEN_WIDTH * scale)))
                image = pygame.transform.smoothscale(image, size)
            # pymunk angles turn clockwise on screen (y points down), pygame rotates counter-clockwise
            image = pygame.transform.rotate(image, -math.degrees(pen.body.angle))
            if fade:
                image.set_alpha(int(255 * (1 - fade)))
            pos = center + offset
            surface.blit(image, image.get_rect(center=(pos.x, pos.y)))
            return

        pygame.draw.polygon(surface, color, corners)
        pygame.draw.polygon(surface, PEN_OUTLINE_COLOR, corners, width=2)

    def _draw_turn_indicator(self, surface: pygame.Surface) -> None:
        pen = self.active_pen
        if not self.shot_in_flight and not self.board.shrinking:
            c = (int(pen.body.position.x), int(pen.body.position.y))
            pygame.draw.circle(surface, TURN_RING_COLOR, c, 18, width=2)
        label = f"Player {self.current + 1}'s turn"
        text = self.big_font.render(label, True, pen.color)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 60)))

        counts = self.font.render(
            f"Shots  P1: {self.shots[0]}   P2: {self.shots[1]}", True, TEXT_COLOR
        )
        surface.blit(counts, counts.get_rect(center=(SCREEN_WIDTH // 2, 90)))

    def _draw_warning_text(self, surface: pygame.Surface) -> None:
        if self.board.target is not None and not self.board.shrinking:
            text = self.big_font.render(
                "WARNING: board shrinks next turn!", True, WARNING_COLOR
            )
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 640 - 40)))

    def _draw_score(self, surface: pygame.Surface) -> None:
        text = self.big_font.render(
            f"P1  {self.scores[0]} - {self.scores[1]}  P2    Round {self.round_number}",
            True,
            TEXT_COLOR,
        )
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 25)))

    def _draw_round_over(self, surface: pygame.Surface) -> None:
        if not self.round_over or not self.round_result_applied:
            return

        if self.match_winner is not None:
            msg = f"Player {self.match_winner + 1} wins the match!"
            sub_text = "Press R for a new match    ESC: menu"
        else:
            if self.last_result == "draw_replay":
                msg = "Draw! Replaying the round"
            elif self.last_result == "draw_decided":
                msg = f"Draw again: Player {self.round_winner + 1} wins (closer to the middle)"
            else:
                msg = f"Player {self.round_winner + 1} wins the round!"
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

        distance = predicted_distance(self._power(pull) * MAX_SHOT_SPEED)
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
        if self.round_over:
            return
        seconds = max(0, int(self.turn_time_left) + 1)
        urgent = self.turn_time_left <= TIMER_WARNING_TIME
        color = WARNING_COLOR if urgent else TEXT_COLOR
        text = self.big_font.render(f"{seconds}", True, color)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH - 90, 60)))

        # Thin bar under the power bar showing the time left
        bar = pygame.Rect(TIMER_BAR_RECT)
        pygame.draw.rect(surface, POWER_BAR_BG_COLOR, bar, border_radius=5)
        ratio = max(0.0, self.turn_time_left / TURN_TIME_LIMIT)
        if ratio > 0:
            fill = bar.copy()
            fill.width = int(bar.width * ratio)
            pygame.draw.rect(surface, color, fill, border_radius=5)