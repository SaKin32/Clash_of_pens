"""Physics world: a flat board, pens as pymunk bodies, no walls."""

from typing import Optional

import pymunk

from common.pen import PenStats
from common.constants import (
    BOARD_RECT,
    PHYSICS_DAMPING,
    PHYSICS_SUBSTEPS,
    PEN_LENGTH,
    PEN_WIDTH,
    PEN_MASS,
    PEN_ELASTICITY,
    PEN_FRICTION,
    PEN_START_HP,
    SETTLE_SPEED,
    SETTLE_ANGULAR_SPEED,
)


class Pen:
    """A pen on the board: one rigid body plus game state (HP)."""

    def __init__(
        self,
        space: pymunk.Space,
        position: tuple,
        angle: float,
        color: tuple,
        stats: Optional[PenStats] = None,
    ):
        # With no stats we fall back to the plain placeholder pen from constants.py
        self.stats = stats
        self.length = stats.length if stats else PEN_LENGTH
        self.width = stats.width if stats else PEN_WIDTH
        mass = stats.mass if stats else PEN_MASS
        size = (self.length, self.width)
        moment = pymunk.moment_for_box(mass, size)
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.body.angle = angle
        self.shape = pymunk.Poly.create_box(self.body, size)
        self.shape.elasticity = stats.elasticity if stats else PEN_ELASTICITY
        self.shape.friction = stats.friction if stats else PEN_FRICTION
        space.add(self.body, self.shape)

        self.color = color
        self.hp = stats.hp if stats else PEN_START_HP

    @property
    def power(self) -> float:
        """Multiplier on the shot speed (1.0 for the placeholder pen)."""
        return self.stats.power if self.stats else 1.0

    def corners(self) -> list:
        """Return the four corners of the pen in world coordinates."""
        return [self.body.local_to_world(v) for v in self.shape.get_vertices()]


class PenWorld:
    """Owns the pymunk space and every pen in it."""

    def __init__(self):
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)  # top-down view, no gravity
        self.space.damping = PHYSICS_DAMPING
        self.pens = []

    def add_pen(
        self, position: tuple, angle: float, color: tuple, stats: Optional[PenStats] = None
    ) -> Pen:
        pen = Pen(self.space, position, angle, color, stats)
        self.pens.append(pen)
        return pen

    def step(self, dt: float) -> None:
        """Advance the simulation by dt seconds using small fixed substeps."""
        dt = min(dt, 1 / 30)  # avoid huge jumps after a lag spike
        for _ in range(PHYSICS_SUBSTEPS):
            self.space.step(dt / PHYSICS_SUBSTEPS)

    def is_settled(self) -> bool:
        """True when every pen has (almost) stopped moving and spinning."""
        for pen in self.pens:
            if pen.body.velocity.length > SETTLE_SPEED:
                return False
            if abs(pen.body.angular_velocity) > SETTLE_ANGULAR_SPEED:
                return False
        return True

    def stop_all(self) -> None:
        """Zero out all motion so tiny leftover drift does not continue."""
        for pen in self.pens:
            pen.body.velocity = (0, 0)
            pen.body.angular_velocity = 0         

    @staticmethod
    def edge_distance(pen: Pen, board: tuple) -> float:
        """Distance from the pen's center to the nearest board edge.

        Positive = inside the board, negative = outside (the pen has fallen).
        """
        x, y, w, h = board
        px, py = pen.body.position
        return min(px - x, x + w - px, py - y, y + h - py)