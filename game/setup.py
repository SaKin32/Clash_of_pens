"""What the player has picked so far on the way to a match (mode, difficulty, pens)."""

from dataclasses import dataclass, field
from typing import List

from common.pen import DEFAULT_PEN_KEY
from game.ai import DEFAULT_DIFFICULTY


@dataclass
class GameSetup:
    mode: str = "pvc"  # "pvc" or "pvp"
    difficulty: str = DEFAULT_DIFFICULTY
    pens: List[str] = field(default_factory=lambda: [DEFAULT_PEN_KEY, DEFAULT_PEN_KEY])
    picking: int = 0  # which player is choosing a pen right now (0 or 1)


setup = GameSetup()


def begin(mode: str) -> GameSetup:
    """Start a fresh setup for a new game."""
    setup.mode = mode
    setup.difficulty = DEFAULT_DIFFICULTY
    setup.pens = [DEFAULT_PEN_KEY, DEFAULT_PEN_KEY]
    setup.picking = 0
    return setup
