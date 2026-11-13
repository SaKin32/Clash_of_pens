"""Match rules: rounds, turns, falling, draws and sudden death.

This file has no drawing code and does not open a window. The match screen, the
computer player and the tests all drive the same Match object, so a match can be
played (and tested) completely headless.

Rules in short:
    * Best of 3 rounds (ROUNDS_TO_WIN).
    * A round ends when a pen's centre leaves the board. The other pen wins it.
    * Each player gets ROUND_TURN_LIMIT turns. With no fall by then it is a draw.
    * The first draw of a match is replayed (MAX_DRAW_REPLAYS).
    * The next draw is settled by sudden death: a small board with fewer turns.
    * If sudden death is also a draw, the pen further from the edge wins.
"""

import math
from typing import Optional, Sequence

import pymunk

from common.constants import (
    BOARD_RECT,
    MAX_SHOT_SPEED,
    MAX_SPIN,
    FALL_DURATION,
    ROUNDS_TO_WIN,
    MAX_DRAW_REPLAYS,
    TURN_TIME_LIMIT,
    ROUND_TURN_LIMIT,
    SUDDEN_DEATH_ENABLED,
    SUDDEN_DEATH_BOARD_SIZE,
    SUDDEN_DEATH_TURN_LIMIT,
    PEN_COLOR_P1,
    PEN_COLOR_P2,
)
from common.pen import DEFAULT_PEN_KEY, get_pen
from game.board import Board
from game.physics import Pen, PenWorld

PLAYER_COLORS = (PEN_COLOR_P1, PEN_COLOR_P2)
MODES = ("pvc", "pvp")
START_OFFSET = 220  # distance of each pen's centre from its side of the board


def apply_flick(pen: Pen, direction, power: float, grab_local=(0, 0)) -> None:
    """Give a pen a flick. direction = where it flies, power = 0..1 (after the power curve).

    The impulse lands on grab_local (a point in the pen's own coordinates), so an
    off-centre grab makes the pen spin. Shared by the match and the computer player.
    """
    body = pen.body
    direction = pymunk.Vec2d(*direction)
    speed = power * MAX_SHOT_SPEED * pen.power
    impulse = direction.normalized() * (speed * body.mass)
    body.apply_impulse_at_world_point(impulse, body.local_to_world(grab_local))
    body.angular_velocity = max(-MAX_SPIN, min(MAX_SPIN, body.angular_velocity))


class Match:
    """One match between two pens. Call step(dt) every frame."""

    def __init__(
        self,
        pen_keys: Sequence[str] = (DEFAULT_PEN_KEY, DEFAULT_PEN_KEY),
        mode: str = "pvp",
        difficulty: Optional[str] = None,
    ):
        self.pen_keys = [get_pen(k).key for k in pen_keys]
        self.mode = mode if mode in MODES else "pvp"
        self.difficulty = difficulty
        self.reset_match()

    # ----- setup -----

    def reset_match(self) -> None:
        """Start a brand new match: scores back to 0-0."""
        self.scores = [0, 0]
        self.draw_replays_used = 0
        self.round_number = 1
        self.rounds_played = 0       # rounds started so far; decides who shoots first
        self.match_winner = None     # 0 or 1 once someone wins the match
        self.last_result = ""        # "win", "draw_replay", "sudden_death" or "draw_decided"
        self.sudden_death_next = False
        self.reset_round()

    def reset_round(self) -> None:
        """Start a fresh board with both pens in place."""
        self.sudden_death = self.sudden_death_next
        self.sudden_death_next = False
        self.world = PenWorld()
        self.board = Board()
        if self.sudden_death:
            self.board.start_small(SUDDEN_DEATH_BOARD_SIZE)
        self.turn_limit = SUDDEN_DEATH_TURN_LIMIT if self.sudden_death else ROUND_TURN_LIMIT

        x, y, w, h = self.board.as_tuple()
        cy = y + h / 2
        offset = min(START_OFFSET, w * 0.28)  # keeps the pens apart on the small board
        self.world.add_pen((x + offset, cy), 0.0, PLAYER_COLORS[0], get_pen(self.pen_keys[0]))
        self.world.add_pen((x + w - offset, cy), math.pi, PLAYER_COLORS[1], get_pen(self.pen_keys[1]))

        self.starter = self.rounds_played % 2  # players take turns shooting first
        self.current = self.starter
        self.rounds_played += 1
        self.turn_id = 0  # goes up by one every time a turn ends
        self.shot_in_flight = False
        self.shots = [0, 0]        # real shots taken by each player
        self.turns_taken = [0, 0]  # turns used by each player, including skipped ones
        self.falling = {}          # pen index -> seconds since it started falling
        self.fallen = []           # pen indices that have fully fallen
        self.round_over = False
        self.draw_by_limit = False  # draw because nobody fell within the turn limit
        self.round_result_applied = False
        self.round_winner = None   # 0 or 1, or None for a replayed draw / sudden death
        self.turn_time_left = TURN_TIME_LIMIT

    def next_round(self) -> bool:
        """Start the next round once the result is shown. False if it is not time yet."""
        if self.match_winner is not None or not self.round_result_applied:
            return False
        self.reset_round()
        return True

    # ----- state -----

    @property
    def active_pen(self) -> Pen:
        return self.world.pens[self.current]

    @property
    def can_shoot(self) -> bool:
        return (
            self.match_winner is None
            and not self.round_over
            and not self.shot_in_flight
            and not self.board.shrinking
        )

    @property
    def waiting_for_next_round(self) -> bool:
        return self.round_over and self.round_result_applied and self.match_winner is None

    # ----- actions -----

    def shoot(self, direction, power: float, grab_local=(0, 0)) -> bool:
        """Flick the active pen. Returns False if a shot is not allowed right now."""
        if not self.can_shoot:
            return False
        if pymunk.Vec2d(*direction).length == 0:
            return False
        apply_flick(self.active_pen, direction, max(0.0, min(1.0, power)), grab_local)
        self.shot_in_flight = True
        self.shots[self.current] += 1
        self.turns_taken[self.current] += 1
        return True

    def skip_turn(self) -> None:
        """Time ran out: the move is lost and the turn passes on."""
        if not self.can_shoot:
            return
        self.turns_taken[self.current] += 1
        self._end_turn()

    # ----- update -----

    def step(self, dt: float) -> None:
        self.world.step(dt)
        self.board.update(dt)
        self._update_falling(dt)

        if self.round_over:
            self._apply_round_result()
            return

        # The timer runs only while the active player is choosing a shot
        if not self.shot_in_flight and not self.board.shrinking:
            self.turn_time_left -= dt
            if self.turn_time_left <= 0:
                self.skip_turn()
                return

        if self.shot_in_flight and self.world.is_settled():
            self.world.stop_all()
            self.shot_in_flight = False
            self._end_turn()

    def _update_falling(self, dt: float) -> None:
        """Detect pens whose centre left the board and animate their fall."""
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

    def _end_turn(self) -> None:
        if self.falling:  # a fallen pen ends the round, no more turns
            return
        self.current = 1 - self.current
        self.turn_time_left = TURN_TIME_LIMIT
        self.turn_id += 1
        # Both players have used the same number of turns: shrink warning or final draw
        if self.turns_taken[0] == self.turns_taken[1]:
            self.board.on_turn_completed(self.turns_taken[0])
            if self.turns_taken[0] >= self.turn_limit:
                self.draw_by_limit = True
                self.round_over = True
                return
        self.board.on_next_turn_started()

    # ----- round result -----

    def _round_winner(self) -> Optional[int]:
        """Return 0 or 1 for the round winner, or None for a draw."""
        if self.draw_by_limit or len(self.fallen) >= 2:
            return None
        if len(self.fallen) == 1:
            return 1 - self.fallen[0]
        return None

    def _closer_to_middle(self) -> int:
        """The pen further inside the board wins a drawn round."""
        board = self.board.as_tuple()
        d0 = PenWorld.edge_distance(self.world.pens[0], board)
        d1 = PenWorld.edge_distance(self.world.pens[1], board)
        return 0 if d0 >= d1 else 1

    def _apply_round_result(self) -> None:
        """Work out who won the round (once), update scores and match state."""
        if self.round_result_applied:
            return
        if not self.draw_by_limit:
            if not self.fallen:
                return  # wait for the fall animation
            if len(self.fallen) < len(self.falling):
                return  # the other pen is still falling too
        self.round_result_applied = True

        winner = self._round_winner()
        if winner is not None:
            self.last_result = "win"
        elif not self.sudden_death and self.draw_replays_used < MAX_DRAW_REPLAYS:
            self.draw_replays_used += 1
            self.last_result = "draw_replay"
        elif SUDDEN_DEATH_ENABLED and not self.sudden_death:
            self.sudden_death_next = True
            self.last_result = "sudden_death"
        else:
            winner = self._closer_to_middle()
            self.last_result = "draw_decided"

        self.round_winner = winner
        if winner is not None:
            self.scores[winner] += 1
            if self.scores[winner] >= ROUNDS_TO_WIN:
                self.match_winner = winner
            else:
                self.round_number += 1

    # ----- save / load -----

    def to_state(self) -> dict:
        """Match-level state for the save file. The round in progress is restarted on resume."""
        in_round = not self.round_result_applied  # this round is not finished yet
        return {
            "mode": self.mode,
            "difficulty": self.difficulty,
            "pens": list(self.pen_keys),
            "score": list(self.scores),
            "round": self.round_number,
            "draw_replays_used": self.draw_replays_used,
            "rounds_played": self.rounds_played - 1 if in_round else self.rounds_played,
            "sudden_death_next": bool(self.sudden_death_next or (in_round and self.sudden_death)),
        }

    @classmethod
    def from_state(cls, state: dict) -> "Match":
        """Rebuild a match from a save. Bad or missing fields fall back to safe defaults."""

        def whole(value, default, low, high):
            if isinstance(value, int) and not isinstance(value, bool):
                return max(low, min(high, value))
            return default

        pens = state.get("pens")
        if not (isinstance(pens, (list, tuple)) and len(pens) == 2):
            pens = (DEFAULT_PEN_KEY, DEFAULT_PEN_KEY)
        pens = [p if isinstance(p, str) else DEFAULT_PEN_KEY for p in pens]
        difficulty = state.get("difficulty")
        match = cls(pens, mode=state.get("mode", "pvp"),
                    difficulty=difficulty if isinstance(difficulty, str) else None)

        score = state.get("score")
        if isinstance(score, (list, tuple)) and len(score) == 2:
            match.scores = [whole(s, 0, 0, ROUNDS_TO_WIN - 1) for s in score]
        match.round_number = whole(state.get("round"), sum(match.scores) + 1, 1, 99)
        match.draw_replays_used = whole(state.get("draw_replays_used"), 0, 0, MAX_DRAW_REPLAYS)
        match.rounds_played = whole(state.get("rounds_played"), sum(match.scores), 0, 999)
        match.sudden_death_next = bool(state.get("sudden_death_next")) and SUDDEN_DEATH_ENABLED
        match.reset_round()
        return match
