"""Match screen: draws a Match and turns mouse input into flicks.

The rules live in game/match.py and the computer player in game/ai.py. This file
only shows the match, reads the mouse, pauses, and saves.
"""

import math
import random
from typing import Optional

import pygame
from game import music
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
from game.assets import load_image, load_font
from game.badge_button import outlined_text
from game.icon_button import IconButton
from game.match_art import pen_sprite, table_texture, bench_background
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
        self.font = load_font(FONT_SIZE_SMALL)
        self.big_font = load_font(FONT_SIZE_BUTTON)
        self.huge_font = load_font(FONT_SIZE_HEADING)

        self.match = Match()
        self.ai: Optional[AIPlayer] = None
        self.paused = False
        self.dragging = False
        self.drag_pen = 0        # index of the pen being pulled back
        self.grab_local = pymunk.Vec2d(0, 0)
        self._turn_id = -1       # used to notice that a new turn began
        self._ai_wait = 0.0      # seconds left before the computer flicks
        self._save_cleared = False
        self._drop_sounds_played = set()

        self.pause_icon = IconButton("pause.png", (24, 20), self.on_toggle_pause)

        self.pause_buttons = [
            Button("Resume", self._pause_rect(0), self.on_resume),
            Button("Restart Match", self._pause_rect(1), self.on_restart_match),
            Button("Main Menu", self._pause_rect(2), self.on_main_menu),
            Button("How to Play", self._pause_rect(3), self.on_how_to_play),
            Button("", self._pause_rect(4), self.on_toggle_music),
        ]
        self.music_btn = self.pause_buttons[4]

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
        self._drop_sounds_played.clear()

    def resume_from_save(self, state: dict) -> None:
        self.start(Match.from_state(state))

    # ----- pause menu -----

    @staticmethod
    def _pause_rect(index: int) -> tuple:
        x = (SCREEN_WIDTH - PAUSE_BUTTON_WIDTH) // 2
        y = 200 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        return (x, y, PAUSE_BUTTON_WIDTH, BUTTON_HEIGHT)

    def _update_music_label(self) -> None:
        self.music_btn.text = "Music: On" if settings.is_music_on() else "Music: Off"

    def on_enter(self) -> None:
        self._update_music_label()
        music.stop()

    def on_toggle_pause(self) -> None:
        self.paused = not self.paused
        self.dragging = False
        self._update_music_label()

    def on_resume(self) -> None:
        self.paused = False

    def on_restart_match(self) -> None:
        self.match.reset_match()
        self.paused = False
        self.dragging = False
        self._turn_id = -1
        self._save_cleared = False
        self._drop_sounds_played.clear()
        if self.match.mode == "pvc":
            self.ai = AIPlayer(self.match.difficulty or "medium")
            self._ai_wait = random.uniform(*AI_THINK_TIME)
        else:
            self.ai = None
        save.delete_save()

    def on_main_menu(self) -> None:
        self.paused = False
        self.dragging = False
        if self.match.match_winner is None:
            self._save_match()
        self.manager.switch("mode_select")

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
        return self.match.world.pens[self.drag_pen].body.local_to_world(self.grab_local)

    def _pull_vector(self, mouse_pos: tuple) -> pymunk.Vec2d:
        pull = self._grab_world() - pymunk.Vec2d(*mouse_pos)
        if pull.length > MAX_PULL_DISTANCE:
            pull = pull.normalized() * MAX_PULL_DISTANCE
        return pull

    @staticmethod
    def _power(pull: pymunk.Vec2d) -> float:
        return (pull.length / MAX_PULL_DISTANCE) ** POWER_CURVE

    def _grabbed(self, mouse_pos: tuple) -> Optional[int]:
        """Index of the current team's pen under the mouse (the closest one), or None."""
        m = self.match
        best, best_distance = None, GRAB_MARGIN
        for i in m.alive_indexes(m.current):
            distance = m.world.pens[i].shape.point_query(mouse_pos).distance
            if distance <= best_distance:
                best, best_distance = i, distance
        return best

    def _fire(self, mouse_pos: tuple) -> None:
        pull = self._pull_vector(mouse_pos)
        if pull.length < MIN_PULL_DISTANCE:
            return
        power = self._power(pull)
        self.match.shoot(pull, power, self.grab_local, self.drag_pen)
        # Table friction sound: volume scales directly with pull power
        # Light flick = gentle sound, strong pull = loud friction slide
        vol = max(0.2, min(1.0, 0.25 + power * 0.75))
        music.play_sound("pen_slide", volume=vol)

    def _player_label(self, index: int) -> str:
        if self.ai is not None and index == AI_PLAYER_INDEX:
            return "Computer"
        if self.match.team_size > 1:
            return f"Team {index + 1}"
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

        self.pause_icon.handle_event(event)
        if self.paused:
            return

        if not m.can_shoot or not self._human_turn:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pen_index = self._grabbed(event.pos)
            if pen_index is not None:
                self.drag_pen = pen_index
                pen = m.world.pens[pen_index]
                local = pen.body.world_to_local(event.pos)
                # A click just past the head or tail still counts as the very end of the pen
                self.grab_local = pymunk.Vec2d(
                    max(-pen.length / 2, min(pen.length / 2, local.x)),
                    max(-pen.width / 2, min(pen.width / 2, local.y)),
                )
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

        # Play pen drop sound when a falling pen hits the floor
        if not m.falling and self._drop_sounds_played:
            self._drop_sounds_played.clear()
        for pen_idx, fall_time in m.falling.items():
            if fall_time >= FALL_DURATION * 0.70 and pen_idx not in self._drop_sounds_played:
                self._drop_sounds_played.add(pen_idx)
                music.play_sound("pen_drop", volume=0.95)

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
                m.shoot(shot.direction, shot.power, shot.grab)
                vol = max(0.2, min(1.0, 0.25 + shot.power * 0.75))
                music.play_sound("pen_slide", volume=vol)

        # A finished match cannot be resumed, so remove its save
        if m.match_winner is not None and not self._save_cleared:
            save.delete_save()
            self._save_cleared = True

    # ----- drawing -----

    def draw(self, surface: pygame.Surface) -> None:
        m = self.match
        bench = bench_background()
        if bench:
            surface.blit(bench, (0, 0))
            # Soft atmospheric dimming over the background
            dark_dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            dark_dim.fill((0, 0, 0, 65))
            surface.blit(dark_dim, (0, 0))
        else:
            bg = load_image("match_bg.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
            if bg:
                surface.blit(bg, (0, 0))
            else:
                surface.fill(BG_COLOR)
        self._draw_board(surface)

        for i, pen in enumerate(m.world.pens):
            self._draw_pen(surface, i, pen)

        self._draw_impacts(surface)

        if self.dragging:
            self._draw_aim(surface)
        self._draw_scoreboard(surface)
        self._draw_warning_text(surface)
        self._draw_timer(surface)
        self._draw_round_over(surface)

        if not self.paused and not m.round_over:
            self.pause_icon.draw(surface)

        if self.paused:
            self._draw_pause(surface)

    def _draw_board(self, surface: pygame.Surface) -> None:
        m = self.match
        board = pygame.Rect(m.board.as_tuple())
        table = table_texture()
        if table is not None and board.width > 0 and board.height > 0:
            # Draw realistic drop shadow under the table
            shadow_rect = board.inflate(14, 14).move(0, 8)
            pygame.draw.rect(surface, (0, 0, 0, 110), shadow_rect, border_radius=32)

            # Show the part of the table that is still inside the (shrinking) board
            area = board.move(-BOARD_RECT[0], -BOARD_RECT[1]).clip(table.get_rect())
            table_sub = table.subsurface(area).copy()

            # Rounded mask for smooth edges
            mask_surf = pygame.Surface(board.size, pygame.SRCALPHA)
            pygame.draw.rect(mask_surf, (255, 255, 255, 255), (0, 0, board.width, board.height), border_radius=28)
            table_sub.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            surface.blit(table_sub, (BOARD_RECT[0] + area.x, BOARD_RECT[1] + area.y))
        else:
            pygame.draw.rect(surface, BOARD_COLOR, board, border_radius=28)

        # Elegant double border like real wooden tables
        pygame.draw.rect(surface, (45, 25, 15), board, width=6, border_radius=28)
        pygame.draw.rect(surface, (90, 55, 30), board.inflate(-8, -8), width=3, border_radius=24)

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
        if pen.removed:
            return
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
        image = pen_sprite(key, pen.length, pen.width)
        if image:
            if scale < 1.0:
                size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
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

    def _draw_impacts(self, surface: pygame.Surface) -> None:
        impacts = getattr(self.match.world, "impacts", None)
        if not impacts:
            return
        for imp in impacts:
            if not imp.get("sound_played", False):
                imp["sound_played"] = True
                impulse = imp.get("impulse", 500.0)
                vol = max(0.3, min(1.0, impulse / 1200.0))
                music.play_sound("touching-and-shooting-pen", volume=vol)

            ratio = max(0.0, min(1.0, imp["life"] / imp["max_life"]))
            radius = int(14 * (1.0 - ratio) + 4)
            alpha = int(220 * ratio)
            pos = (int(imp["pos"].x), int(imp["pos"].y))
            flash = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 235, 170, alpha), (radius + 2, radius + 2), radius, width=2)
            pygame.draw.circle(flash, (255, 255, 255, int(alpha * 0.7)), (radius + 2, radius + 2), max(1, radius // 2))
            surface.blit(flash, (pos[0] - radius - 2, pos[1] - radius - 2))

    def _draw_pen_names(self, surface: pygame.Surface) -> None:
        m = self.match
        for i, x in ((0, 200), (1, SCREEN_WIDTH - 200)):
            if m.team_size > 1:
                alive = len(m.alive_indexes(i))
                info = f"{alive} of {m.team_size} pens left"
            else:
                info = get_pen(m.pen_keys[i]).name
            text = self.font.render(f"{self._player_label(i)}: {info}", True, PLAYER_COLORS[i])
            rect = text.get_rect(midleft=(x, 60)) if i == 0 else text.get_rect(midright=(x, 60))
            surface.blit(text, rect)

    def _draw_warning_text(self, surface: pygame.Surface) -> None:
        m = self.match
        if m.board.target is not None and not m.board.shrinking:
            text = outlined_text(
                self.big_font, "WARNING: board shrinks next turn!", WARNING_COLOR, outline=3
            )
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 640 - 40)))
        elif m.sudden_death and not m.round_over:
            text = outlined_text(self.big_font, "SUDDEN DEATH", WARNING_COLOR, outline=3)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 640 - 40)))

    def _draw_score(self, surface: pygame.Surface) -> None:
        m = self.match
        label = f"P1  {m.scores[0]} - {m.scores[1]}  P2    Round {m.round_number}"
        if self.ai is not None:
            label = f"You  {m.scores[0]} - {m.scores[1]}  CPU    Round {m.round_number}"
        text = outlined_text(self.big_font, label, TEXT_COLOR, outline=2)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 25)))

    def _draw_round_over(self, surface: pygame.Surface) -> None:
        m = self.match
        if not m.round_over or not m.round_result_applied:
            return

        note = ""
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
            if m.draw_by_limit and m.last_result == "win":
                note = "Turn limit reached: more pens left on the board"

        text = outlined_text(self.huge_font, msg, FALL_BANNER_COLOR, outline=4)
        surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        sub = outlined_text(self.big_font, sub_text, TEXT_COLOR, outline=3)
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 56)))
        if note:
            note_surf = outlined_text(self.font, note, TEXT_COLOR, outline=2)
            surface.blit(note_surf, note_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 96)))

    def _draw_aim(self, surface: pygame.Surface) -> None:
        pull = self._pull_vector(pygame.mouse.get_pos())
        if pull.length < MIN_PULL_DISTANCE:
            return
        start = self._grab_world()
        power = self._power(pull)
        rating = int(round(power * 100))

        # 1. Forward Trajectory & Targeting Arrow
        direction = pull.normalized()
        forward_dir = pygame.Vector2(direction.x, direction.y)
        speed = power * MAX_SHOT_SPEED * self.match.world.pens[self.drag_pen].power
        distance = min(360.0, predicted_distance(speed))

        # Forward guide line and arrow head
        if distance > 24:
            arrow_len = min(distance, 150.0)
            p_arrow_tip = start + direction * arrow_len
            arrow_end = start + direction * max(20.0, arrow_len - 14)
            pygame.draw.line(surface, (235, 75, 55), (int(start.x), int(start.y)), (int(arrow_end.x), int(arrow_end.y)), 6)

            # Arrow head
            perp = pygame.Vector2(-direction.y, direction.x)
            h1 = p_arrow_tip - direction * 18 + perp * 11
            h2 = p_arrow_tip - direction * 18 - perp * 11
            pygame.draw.polygon(surface, (235, 75, 55), [
                (int(p_arrow_tip.x), int(p_arrow_tip.y)),
                (int(h1.x), int(h1.y)),
                (int(h2.x), int(h2.y))
            ])

            # Projected dashed flight path beyond arrow
            step = 22
            for d in range(int(arrow_len) + 16, int(distance), step):
                dot = start + direction * d
                pygame.draw.circle(surface, (240, 110, 90), (int(dot.x), int(dot.y)), 3)

        # 2. Backward Pull Segmented Bar (Image 2 style)
        pull_dist = pull.length
        pull_dir = -direction
        seg_count = 3
        seg_len = pull_dist / seg_count

        for s in range(seg_count):
            p1 = start + pull_dir * (s * seg_len + 8)
            p2 = start + pull_dir * ((s + 1) * seg_len)
            pygame.draw.line(surface, (230, 80, 60), (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 16)
            pygame.draw.line(surface, (255, 140, 110), (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 8)
            if s > 0:
                notch = start + pull_dir * (s * seg_len + 4)
                pygame.draw.circle(surface, (160, 40, 30), (int(notch.x), int(notch.y)), 4)

        # Grab circle on pen
        pygame.draw.circle(surface, (255, 255, 255), (int(start.x), int(start.y)), 8)
        pygame.draw.circle(surface, (235, 75, 55), (int(start.x), int(start.y)), 5)

        # 3. Circular Power Rating Badge (Image 2 style: rounded badge with 0-100 rating)
        drag_pos = start - pull
        badge_center = (int(drag_pos.x), int(drag_pos.y))
        pygame.draw.circle(surface, (245, 240, 235), badge_center, 22)
        pygame.draw.circle(surface, (215, 65, 45), badge_center, 22, width=3)
        badge_txt = self.font.render(str(rating), True, (25, 20, 20))
        surface.blit(badge_txt, badge_txt.get_rect(center=badge_center))

    def _draw_scoreboard(self, surface: pygame.Surface) -> None:
        """Top Scoreboard banner with player profile cards, score slots, and round badge."""
        m = self.match
        board_w, board_h = 620, 62
        bx = (SCREEN_WIDTH - board_w) // 2
        by = 16

        rd_w, rd_h = 66, 68
        rd_x = SCREEN_WIDTH // 2 - rd_w // 2
        rd_y = by - 4

        p1_rect = pygame.Rect(bx, by, (board_w - rd_w) // 2, board_h)
        p2_rect = pygame.Rect(SCREEN_WIDTH // 2 + rd_w // 2, by, (board_w - rd_w) // 2, board_h)

        # Drop shadow for scoreboard
        pygame.draw.rect(surface, (0, 0, 0, 90), p1_rect.move(0, 4), border_top_left_radius=20, border_bottom_left_radius=20)
        pygame.draw.rect(surface, (0, 0, 0, 90), p2_rect.move(0, 4), border_top_right_radius=20, border_bottom_right_radius=20)
        pygame.draw.rect(surface, (0, 0, 0, 90), pygame.Rect(rd_x, rd_y + 4, rd_w, rd_h), border_radius=12)

        # P1 background (Warm orange/brown gradient)
        pygame.draw.rect(surface, (190, 85, 25), p1_rect, border_top_left_radius=20, border_bottom_left_radius=20)
        pygame.draw.rect(surface, (240, 140, 60), p1_rect, width=3, border_top_left_radius=20, border_bottom_left_radius=20)

        # P2 background (Dark charcoal / metallic)
        pygame.draw.rect(surface, (55, 50, 48), p2_rect, border_top_right_radius=20, border_bottom_right_radius=20)
        pygame.draw.rect(surface, (110, 100, 95), p2_rect, width=3, border_top_right_radius=20, border_bottom_right_radius=20)

        # Center Round Badge
        pygame.draw.rect(surface, (35, 32, 30), (rd_x, rd_y, rd_w, rd_h), border_radius=12)
        pygame.draw.rect(surface, (150, 135, 120), (rd_x, rd_y, rd_w, rd_h), width=3, border_radius=12)

        # P1 Avatar badge
        p1_avatar_center = (bx + 32, by + board_h // 2)
        pygame.draw.circle(surface, (240, 140, 60), p1_avatar_center, 28)
        pygame.draw.circle(surface, (255, 235, 210), p1_avatar_center, 22)
        p1_label = self.font.render("P1", True, (190, 85, 25))
        surface.blit(p1_label, p1_label.get_rect(center=p1_avatar_center))

        # P2 Avatar badge
        p2_avatar_center = (bx + board_w - 32, by + board_h // 2)
        pygame.draw.circle(surface, (140, 135, 130), p2_avatar_center, 28)
        pygame.draw.circle(surface, (230, 225, 220), p2_avatar_center, 22)
        p2_tag = "CPU" if self.ai is not None else "P2"
        p2_label = self.font.render(p2_tag, True, (55, 50, 48))
        surface.blit(p2_label, p2_label.get_rect(center=p2_avatar_center))

        # Names with black outline
        name1 = outlined_text(self.font, self._player_label(0), (255, 255, 255), outline=2)
        surface.blit(name1, (bx + 72, by + 8))
        name2 = outlined_text(self.font, self._player_label(1), (255, 255, 255), outline=2)
        surface.blit(name2, name2.get_rect(topright=(bx + board_w - 72, by + 8)))

        # Round Score Slots (First to 3 wins)
        for i in range(3):
            # P1 score pills
            c1 = (255, 220, 100) if i < m.scores[0] else (90, 40, 10)
            pygame.draw.rect(surface, c1, (bx + 72 + i * 22, by + 34, 16, 18), border_radius=4)
            pygame.draw.rect(surface, (255, 200, 50), (bx + 72 + i * 22, by + 34, 16, 18), width=1, border_radius=4)
            # P2 score pills
            c2 = (255, 220, 100) if i < m.scores[1] else (30, 25, 25)
            pygame.draw.rect(surface, c2, (bx + board_w - 72 - (3 - i) * 22, by + 34, 16, 18), border_radius=4)
            pygame.draw.rect(surface, (120, 115, 110), (bx + board_w - 72 - (3 - i) * 22, by + 34, 16, 18), width=1, border_radius=4)

        # Round Badge text with black outline
        r_num = outlined_text(self.big_font, str(m.round_number), (255, 255, 255), outline=2)
        r_txt = outlined_text(self.font, "RD", (220, 205, 190), outline=2)
        surface.blit(r_num, r_num.get_rect(center=(SCREEN_WIDTH // 2, rd_y + 20)))
        surface.blit(r_txt, r_txt.get_rect(center=(SCREEN_WIDTH // 2, rd_y + 46)))

    def _draw_timer(self, surface: pygame.Surface) -> None:
        m = self.match
        if m.round_over:
            return
        urgent = m.turn_time_left <= TIMER_WARNING_TIME
        color = WARNING_COLOR if urgent else TEXT_COLOR

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
        title = outlined_text(self.huge_font, "Paused", FALL_BANNER_COLOR, outline=4)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))
        for button in self.pause_buttons:
            button.draw(surface)