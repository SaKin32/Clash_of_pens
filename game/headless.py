"""Play whole matches without a window: computer against computer.

Used by the balance tests, and handy for tuning. Run it to see how the pens and
difficulties compare:

    python -m game.headless            # pen vs pen win rates (Medium AI)
    python -m game.headless 20         # 20 matches per pairing
"""

import random
import sys
from dataclasses import dataclass
from typing import Sequence

from common.pen import PEN_ORDER
from game.ai import AIPlayer
from game.match import Match

FRAME = 1 / 60
MAX_FRAMES = 60 * 60 * 30  # 30 minutes of game time: a safety stop, never reached normally


@dataclass
class MatchResult:
    winner: int          # 0 or 1
    scores: list
    rounds: int          # rounds played, including replays
    sudden_deaths: int   # rounds decided by sudden death
    frames: int


def play_match(
    pen_keys: Sequence[str] = ("ball_pen", "ball_pen"),
    difficulties: Sequence[str] = ("medium", "medium"),
    seed: int = 0,
) -> MatchResult:
    """Play one full match between two computer players and return what happened."""
    rng = random.Random(seed)
    match = Match(pen_keys)
    ais = [AIPlayer(d, random.Random(rng.random())) for d in difficulties]
    sudden_deaths = frames = 0

    while match.match_winner is None:
        if frames > MAX_FRAMES:
            raise RuntimeError("match did not finish")
        if match.waiting_for_next_round:
            if match.last_result == "sudden_death":
                sudden_deaths += 1  # the round about to start is a sudden death
            match.next_round()
        elif match.can_shoot:
            shot = ais[match.current].choose_shot(match)
            match.shoot(shot.direction, shot.power, shot.grab)
        match.step(FRAME)
        frames += 1

    return MatchResult(match.match_winner, list(match.scores), match.rounds_played, sudden_deaths, frames)


def win_rate(pen_a: str, pen_b: str, difficulty: str = "medium", matches: int = 10) -> float:
    """Share of matches pen_a wins against pen_b. Sides swap every match to stay fair."""
    wins = 0
    for n in range(matches):
        if n % 2 == 0:
            wins += play_match((pen_a, pen_b), (difficulty, difficulty), seed=n).winner == 0
        else:
            wins += play_match((pen_b, pen_a), (difficulty, difficulty), seed=n).winner == 1
    return wins / matches


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"Win rate of the row pen against the column pen ({n} Medium-AI matches each)")
    print(" " * 14 + "".join(f"{k[:10]:>12}" for k in PEN_ORDER))
    for a in PEN_ORDER:
        row = "".join(
            f"{'-':>12}" if a == b else f"{win_rate(a, b, matches=n):>12.0%}" for b in PEN_ORDER
        )
        print(f"{a:<14}{row}")
