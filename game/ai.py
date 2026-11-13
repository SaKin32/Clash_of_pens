"""Computer player: three difficulties, one brain.

How it thinks (Medium and Hard):
    1. Make a list of candidate flicks (an angle and a power each).
    2. Play each one out in a private copy of the board, using the same physics.
    3. Score the result: opponent near the edge or off it is good, my own pen near
       the edge or off it is bad.
    4. Pick the best flick, then add a little human-like error (the "noise").

Easy never looks ahead: it aims roughly at the opponent with a lot of error.
Change the numbers in PROFILES to make a difficulty easier or harder.
"""

import math
import random
from dataclasses import dataclass
from typing import Optional, Tuple

import pymunk

from common.constants import AI_MIN_POWER, AI_SIM_FPS, AI_SIM_MAX_FRAMES
from game.match import Match, apply_flick
from game.physics import PenWorld


@dataclass(frozen=True)
class AiProfile:
    name: str
    candidates: int           # flicks tried in the AI's head (0 = no look-ahead)
    spread: float             # candidate angles stay within +/- this many radians of the opponent
    wild_candidates: int      # extra candidates in completely random directions
    aim_noise: float          # standard deviation of the aiming error (radians)
    power_noise: float        # standard deviation of the power error (fraction)
    power_range: Tuple[float, float]  # power range for random flicks (Easy only)
    blunder_chance: float     # chance of a flick in a random direction (Easy only)
    safety: float             # how much the AI cares about keeping its own pen inside


PROFILES = {
    "easy": AiProfile("Easy", 0, 0.0, 0, 0.30, 0.25, (0.35, 0.85), 0.15, 0.0),
    "medium": AiProfile("Medium", 18, 0.45, 0, 0.07, 0.10, (0.3, 1.0), 0.0, 0.35),
    "hard": AiProfile("Hard", 70, 0.8, 8, 0.015, 0.03, (0.25, 1.0), 0.0, 0.5),
}
DIFFICULTIES = tuple(PROFILES.keys())
DEFAULT_DIFFICULTY = "medium"

WIN_SCORE = 1000.0   # opponent fell, mine did not
SAFE_MARGIN = 150.0  # beyond this distance from the edge, extra room does not matter


@dataclass(frozen=True)
class Shot:
    """A chosen flick. angle is the flight direction in radians (pymunk coordinates)."""

    angle: float
    power: float  # 0..1, after the power curve

    @property
    def direction(self) -> pymunk.Vec2d:
        return pymunk.Vec2d(math.cos(self.angle), math.sin(self.angle))


class AIPlayer:
    """Chooses a shot for whoever's turn it is in a Match."""

    def __init__(self, difficulty: str = DEFAULT_DIFFICULTY, rng: Optional[random.Random] = None):
        self.difficulty = difficulty if difficulty in PROFILES else DEFAULT_DIFFICULTY
        self.profile = PROFILES[self.difficulty]
        self.rng = rng or random.Random()

    # ----- public -----

    def choose_shot(self, match: Match) -> Shot:
        me = match.current
        opp = 1 - me
        mine = match.world.pens[me].body.position
        theirs = match.world.pens[opp].body.position
        to_opp = math.atan2(theirs.y - mine.y, theirs.x - mine.x)

        if self.profile.candidates == 0:
            return self._easy_shot(to_opp)

        best, best_score = None, -math.inf
        for angle, power in self._candidates(to_opp):
            score = self._simulate(match, me, angle, power)
            if score > best_score:
                best, best_score = (angle, power), score
        angle, power = best
        return self._with_noise(angle, power)

    # ----- Easy -----

    def _easy_shot(self, to_opp: float) -> Shot:
        p = self.profile
        if self.rng.random() < p.blunder_chance:
            angle = self.rng.uniform(-math.pi, math.pi)
        else:
            angle = to_opp
        power = self.rng.uniform(*p.power_range)
        return self._with_noise(angle, power)

    # ----- Medium / Hard -----

    def _candidates(self, to_opp: float):
        p = self.profile
        rng = self.rng
        # Always try straight at the opponent with a few different powers
        for power in (0.5, 0.7, 0.85, 1.0):
            yield to_opp, power
        for _ in range(max(0, p.candidates - 4)):
            yield to_opp + rng.uniform(-p.spread, p.spread), rng.uniform(*p.power_range)
        for _ in range(p.wild_candidates):
            yield rng.uniform(-math.pi, math.pi), rng.uniform(*p.power_range)

    def _with_noise(self, angle: float, power: float) -> Shot:
        p = self.profile
        angle += self.rng.gauss(0, p.aim_noise)
        power *= 1 + self.rng.gauss(0, p.power_noise)
        return Shot(angle, max(AI_MIN_POWER, min(1.0, power)))

    def _simulate(self, match: Match, me: int, angle: float, power: float) -> float:
        """Play one flick out in a private copy of the board and score the result."""
        opp = 1 - me
        sim = PenWorld()
        for pen in match.world.pens:
            copy = sim.add_pen(tuple(pen.body.position), pen.body.angle, pen.color, pen.stats)
            copy.body.velocity = (0, 0)

        # The board that will matter: if it is about to shrink, judge against the smaller one
        board = tuple(match.board.target) if match.board.target is not None else match.board.as_tuple()
        live_board = match.board.as_tuple()

        apply_flick(sim.pens[me], Shot(angle, power).direction, power)
        fell = [False, False]
        for _ in range(AI_SIM_MAX_FRAMES):
            sim.step(1 / AI_SIM_FPS)
            for i, pen in enumerate(sim.pens):
                if PenWorld.edge_distance(pen, live_board) < 0:
                    fell[i] = True
            if fell[0] or fell[1] or sim.is_settled():
                break

        if fell[opp] and not fell[me]:
            return WIN_SCORE
        if fell[me] and not fell[opp]:
            return -WIN_SCORE
        if fell[me] and fell[opp]:
            return -WIN_SCORE / 5

        my_edge = PenWorld.edge_distance(sim.pens[me], board)
        opp_edge = PenWorld.edge_distance(sim.pens[opp], board)
        return -opp_edge + self.profile.safety * min(my_edge, SAFE_MARGIN)
