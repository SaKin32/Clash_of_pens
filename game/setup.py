"""What the player has picked so far on the way to a match (mode, difficulty, pens)."""

from dataclasses import dataclass, field
from typing import List

from common.constants import MAX_TEAM_SIZE
from common.pen import DEFAULT_PEN_KEY
from game.ai import DEFAULT_DIFFICULTY


@dataclass
class GameSetup:
    mode: str = "pvc"  # "pvc", "pvp" or "team"
    difficulty: str = DEFAULT_DIFFICULTY
    team_size: int = 1  # pens per team: 1, 2 or 3
    # One pen per slot. Team 1's pens come first, then team 2's (matches Match.pen_keys).
    pens: List[str] = field(default_factory=lambda: [DEFAULT_PEN_KEY] * (2 * MAX_TEAM_SIZE))
    picking: int = 0  # which pen slot is being chosen right now

    @property
    def picks_needed(self) -> int:
        """How many pens the players choose in total (the computer picks its own)."""
        return 1 if self.mode == "pvc" else 2 * self.team_size

    @property
    def picking_player(self) -> int:
        """Which player (0 or 1) is choosing the current pen."""
        return 0 if self.mode == "pvc" else self.picking // self.team_size


setup = GameSetup()


def begin(mode: str) -> GameSetup:
    """Start a fresh setup for a new game."""
    setup.mode = mode
    setup.difficulty = DEFAULT_DIFFICULTY
    setup.team_size = 1
    setup.pens = [DEFAULT_PEN_KEY] * (2 * MAX_TEAM_SIZE)
    setup.picking = 0
    return setup


def set_team_size(size: int) -> None:
    setup.team_size = max(1, min(MAX_TEAM_SIZE, size))
    setup.picking = 0
