"""Shrinking board: tracks the current playing area and the warning box."""

from typing import Optional

from common.constants import (
    BOARD_RECT,
    SHRINK_WARNING_TURNS,
    SHRINK_EVERY_TURNS,
    SHRINK_STEP,
    MIN_BOARD_SIZE,
    SHRINK_DURATION,
    MAX_SHRINKS,
)


class Board:
    """The playing surface. Shrinks in steps after a warning."""

    def __init__(self):
        x, y, w, h = BOARD_RECT
        self.rect = [float(x), float(y), float(w), float(h)]
        self.target: Optional[list] = None  # warning box the board will shrink to
        self.start: Optional[list] = None  # board rect when the shrink began
        self.progress = 0.0  # 0..1 while shrinking
        self.shrinking = False
        self.shrink_count = 0
        self.next_event_turn = SHRINK_WARNING_TURNS  # per-player shot count

    # ----- state -----

    @property
    def maxed(self) -> bool:
        """True once the board has shrunk the maximum number of times."""
        return self.shrink_count >= MAX_SHRINKS

    @property
    def at_minimum(self) -> bool:
        return self.rect[2] <= MIN_BOARD_SIZE[0] and self.rect[3] <= MIN_BOARD_SIZE[1]

    def _next_target(self) -> list:
        x, y, w, h = self.rect
        min_w, min_h = MIN_BOARD_SIZE
        step_x = min(SHRINK_STEP, max(0.0, (w - min_w) / 2))
        step_y = min(SHRINK_STEP, max(0.0, (h - min_h) / 2))
        return [x + step_x, y + step_y, w - 2 * step_x, h - 2 * step_y]

    # ----- turn hooks -----

    def on_turn_completed(self, shots_per_player: int) -> None:
        """Call after each full round of turns (both players shot once).

        Shows the warning box when the shot count reaches the next event.
        """
        if self.shrinking or self.at_minimum or self.maxed:
            return
        if shots_per_player >= self.next_event_turn and self.target is None:
            self.target = self._next_target()

    def on_next_turn_started(self) -> None:
        """Call when a new turn begins. Starts the shrink if a warning is showing."""
        if self.target is not None and not self.shrinking:
            self.start = list(self.rect)
            self.progress = 0.0
            self.shrinking = True

    # ----- animation -----

    def update(self, dt: float) -> None:
        if not self.shrinking:
            return
        self.progress = min(1.0, self.progress + dt / SHRINK_DURATION)
        t = self.progress * self.progress * (3 - 2 * self.progress)  # smooth ease
        for i in range(4):
            self.rect[i] = self.start[i] + (self.target[i] - self.start[i]) * t
        if self.progress >= 1.0:
            self.rect = list(self.target)
            self.target = None
            self.start = None
            self.shrinking = False
            self.shrink_count += 1
            self.next_event_turn += SHRINK_EVERY_TURNS

    def as_tuple(self) -> tuple:
        return tuple(self.rect)