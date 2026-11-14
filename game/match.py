"""Match rules: rounds, turns, falling, draws and sudden death.

This file has no drawing code and does not open a window. The match screen, the
computer player and the tests all drive the same Match object, so a match can be
played (and tested) completely headless.

Rules in short:
    * Best of 3 rounds (ROUNDS_TO_WIN).
    * Each team has 1, 2 or 3 pens (1v1, 2v2, 3v3). Teams take turns, and on its turn
      a team flicks any one of its pens that is still on the board.
    * A pen falls when its centre leaves the board. A round ends when a team has no
      pens left; the other team wins it. If both teams lose their last pen together
      it is a draw.
    * Each team gets a turn limit (ROUND_TURN_LIMIT, longer for bigger teams). At the
      limit the team with more pens on the board wins the round. Equal counts = draw.
    * The first draw of a match is replayed (MAX_DRAW_REPLAYS).
    * The next draw is settled by sudden death: a small board with fewer turns.
    * If sudden death is also a draw, the team closer to the middle wins.

Pen numbering: world.pens holds team 0's pens first, then team 1's. With team size N,
pen i belongs to team i // N. In a 1v1 match pen 0 is player 1 and pen 1 is player 2.
"""

import math
from typing import List, Optional, Sequence

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
    MAX_TEAM_SIZE,
    TEAM_TURN_LIMIT_BONUS,
    TEAM_SUDDEN_DEATH_BONUS,
    TEAM_PEN_SPACING,
    PEN_COLOR_P1,
    PEN_COLOR_P2,
)
from common.pen import DEFAULT_PEN_KEY, get_pen
from game.board import Board
from game.physics import Pen, PenWorld

PLAYER_COLORS = (PEN_COLOR_P1, PEN_COLOR_P2)
MODES = ("pvc", "pvp", "team")
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
    """One match between two teams. Call step(dt) every frame."""

    def __init__(
        self,
        pen_keys: Sequence[str] = (DEFAULT_PEN_KEY, DEFAULT_PEN_KEY),
        mode: Optional[str] = None,
        difficulty: Optional[str] = None,
        team_size: Optional[int] = None,
    ):
        keys = list(pen_keys)
        if team_size is None:
            team_size = max(1, len(keys) // 2)
        self.team_size = max(1, min(MAX_TEAM_SIZE, int(team_size)))
        wanted = 2 * self.team_size
        keys = (keys + [DEFAULT_PEN_KEY] * wanted)[:wanted]  # always exactly 2 * team_size pens
        self.pen_keys = [get_pen(k).key for k in keys]

        if mode not in MODES:
            mode = "team" if self.team_size > 1 else "pvp"
        self.mode = mode
        self.difficulty = difficulty
        self.reset_match()

    # ----- team helpers -----

    def team_of(self, pen_index: int) -> int:
        return pen_index // self.team_size

    def pen_indexes(self, team: int) -> List[int]:
        """All pen indexes of a team, fallen or not."""
        return list(range(team * self.team_size, (team + 1) * self.team_size))

    def alive_indexes(self, team: int) -> List[int]:
        """Pen indexes of a team that have not fallen."""
        return [i for i in self.pen_indexes(team) if i not in self.falling]

    def team_eliminated(self, team: int) -> bool:
        return not self.alive_indexes(team)

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

    def _pen_positions(self, team: int, board: tuple) -> List[tuple]:
        """Where a team's pens start: one column on its side of the board, evenly spread."""
        x, y, w, h = board
        cy = y + h / 2
        offset = min(START_OFFSET, w * 0.28)  # keeps the sides apart on the small board
        px = x + offset if team == 0 else x + w - offset
        n = self.team_size
        spacing = h * TEAM_PEN_SPACING
        return [(px, cy + (s - (n - 1) / 2) * spacing) for s in range(n)]

    def reset_round(self) -> None:
        """Start a fresh board with every pen in place."""
        self.sudden_death = self.sudden_death_next
        self.sudden_death_next = False
        self.world = PenWorld()
        self.board = Board()
        if self.sudden_death:
            self.board.start_small(SUDDEN_DEATH_BOARD_SIZE)
        extra = self.team_size - 1
        if self.sudden_death:
            self.turn_limit = SUDDEN_DEATH_TURN_LIMIT + TEAM_SUDDEN_DEATH_BONUS * extra
        else:
            self.turn_limit = ROUND_TURN_LIMIT + TEAM_TURN_LIMIT_BONUS * extra

        board = self.board.as_tuple()
        for team in (0, 1):
            angle = 0.0 if team == 0 else math.pi  # the teams face each other
            positions = self._pen_positions(team, board)
            for slot, index in enumerate(self.pen_indexes(team)):
                self.world.add_pen(
                    positions[slot], angle, PLAYER_COLORS[team], get_pen(self.pen_keys[index])
                )

        self.starter = self.rounds_played % 2  # teams take turns shooting first
        self.current = self.starter
        self.rounds_played += 1
        self.turn_id = 0  # goes up by one every time a turn ends
        self.shot_in_flight = False
        self.shot_pen = None       # index of the pen that was flicked this turn
        self.shots = [0, 0]        # real shots taken by each team
        self.turns_taken = [0, 0]  # turns used by each team, including skipped ones
        self.falling = {}          # pen index -> seconds since it started falling
        self.fallen = []           # pen indexes that have fully fallen
        self.round_over = False
        self.draw_by_limit = False  # the turn limit ended the round
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
        """The pen being flicked, or the current team's first pen still on the board."""
        if self.shot_in_flight and self.shot_pen is not None:
            return self.world.pens[self.shot_pen]
        alive = self.alive_indexes(self.current)
        index = alive[0] if alive else self.pen_indexes(self.current)[0]
        return self.world.pens[index]

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

    def shoot(self, direction, power: float, grab_local=(0, 0), pen_index: Optional[int] = None) -> bool:
        """Flick one of the current team's pens. Returns False if that is not allowed now.

        pen_index picks the pen (it must be on the current team and still on the board).
        Left out, the team's first pen on the board is used, which is the only pen in 1v1.
        """
        if not self.can_shoot:
            return False
        if pymunk.Vec2d(*direction).length == 0:
            return False
        alive = self.alive_indexes(self.current)
        if pen_index is None:
            if not alive:
                return False
            pen_index = alive[0]
        elif pen_index not in alive:
            return False
        apply_flick(self.world.pens[pen_index], direction, max(0.0, min(1.0, power)), grab_local)
        self.shot_in_flight = True
        self.shot_pen = pen_index
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

        # The timer runs only while the active team is choosing a shot
        if not self.shot_in_flight and not self.board.shrinking:
            self.turn_time_left -= dt
            if self.turn_time_left <= 0:
                self.skip_turn()
                return

        if self.shot_in_flight and self.world.is_settled():
            self.world.stop_all()
            self.shot_in_flight = False
            self.shot_pen = None
            self._end_turn()

    def _update_falling(self, dt: float) -> None:
        """Detect pens whose centre left the board, animate their fall, then remove them."""
        board = self.board.as_tuple()
        for i, pen in enumerate(self.world.pens):
            if pen.removed:
                continue
            if i in self.falling:
                self.falling[i] += dt
                if self.falling[i] >= FALL_DURATION and i not in self.fallen:
                    self.fallen.append(i)
                    self.world.remove_pen(pen)  # gone: it can no longer bump the other pens
            elif PenWorld.edge_distance(pen, board) < 0:
                self.falling[i] = 0.0
        # A round ends as soon as one team has lost every pen
        if not self.round_over and (self.team_eliminated(0) or self.team_eliminated(1)):
            self.round_over = True

    def _end_turn(self) -> None:
        if self.round_over:  # no more turns once the round has ended
            return
        self.current = 1 - self.current
        self.turn_time_left = TURN_TIME_LIMIT
        self.turn_id += 1
        # Both teams have used the same number of turns: shrink warning or final draw
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
        if self.draw_by_limit:
            left = [len(self.alive_indexes(t)) for t in (0, 1)]
            if left[0] == left[1]:
                return None
            return 0 if left[0] > left[1] else 1
        out = [t for t in (0, 1) if self.team_eliminated(t)]
        if len(out) == 1:
            return 1 - out[0]
        return None  # both teams lost their last pen together

    def _closer_to_middle(self) -> int:
        """The team whose pens sit further inside the board wins a drawn round."""
        board = self.board.as_tuple()
        totals = [
            sum(PenWorld.edge_distance(self.world.pens[i], board) for i in self.pen_indexes(t))
            for t in (0, 1)
        ]
        return 0 if totals[0] >= totals[1] else 1

    def _apply_round_result(self) -> None:
        """Work out who won the round (once), update scores and match state."""
        if self.round_result_applied:
            return
        if not self.draw_by_limit:
            if not self.fallen:
                return  # wait for the fall animation
            if len(self.fallen) < len(self.falling):
                return  # another pen is still falling
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
            "team_size": self.team_size,
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

        team_size = whole(state.get("team_size"), 1, 1, MAX_TEAM_SIZE)  # old saves have none
        pens = state.get("pens")
        if not isinstance(pens, (list, tuple)) or len(pens) != 2 * team_size:
            pens = [DEFAULT_PEN_KEY] * (2 * team_size)
        pens = [p if isinstance(p, str) else DEFAULT_PEN_KEY for p in pens]
        difficulty = state.get("difficulty")
        match = cls(pens, mode=state.get("mode"),
                    difficulty=difficulty if isinstance(difficulty, str) else None,
                    team_size=team_size)

        score = state.get("score")
        if isinstance(score, (list, tuple)) and len(score) == 2:
            match.scores = [whole(s, 0, 0, ROUNDS_TO_WIN - 1) for s in score]
        match.round_number = whole(state.get("round"), sum(match.scores) + 1, 1, 99)
        match.draw_replays_used = whole(state.get("draw_replays_used"), 0, 0, MAX_DRAW_REPLAYS)
        match.rounds_played = whole(state.get("rounds_played"), sum(match.scores), 0, 999)
        match.sudden_death_next = bool(state.get("sudden_death_next")) and SUDDEN_DEATH_ENABLED
        match.reset_round()
        return match
