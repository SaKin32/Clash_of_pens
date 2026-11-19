"""Physics world: a flat board, pens as pymunk bodies, no walls."""

from typing import Optional

import pymunk

from common.pen import PenStats
from common.constants import (
    BOARD_RECT,
    PHYSICS_DAMPING,
    PHYSICS_SUBSTEPS,
    ANGULAR_DAMPING,
    SPIN_FRICTION,
    PEN_LENGTH,
    PEN_WIDTH,
    PEN_MASS,
    PEN_ELASTICITY,
    PEN_FRICTION,
    PEN_START_HP,
    SETTLE_SPEED,
    SETTLE_ANGULAR_SPEED,
)


def pen_silhouette_vertices(length: float, width: float, key: Optional[str] = None) -> list:
    """Return 8 convex vertices matching the real tapered silhouette of the pen.

    A real pen tapers at the tip (positive X) and has a rounded cap (negative X).
    Using a tapered convex polygon removes the empty transparent 90-degree corners that
    cause phantom collisions before the visible sprite touches the opponent.
    """
    half_l = length / 2
    half_w = width / 2
    if key == "highlighter":
        return [
            (-half_l, -half_w * 0.60),
            (-half_l + 18, -half_w),
            (half_l - 28, -half_w),
            (half_l, -half_w * 0.22),
            (half_l, half_w * 0.22),
            (half_l - 28, half_w),
            (-half_l + 18, half_w),
            (-half_l, half_w * 0.60),
        ]
    else:
        return [
            (-half_l, -half_w * 0.60),
            (-half_l + 14, -half_w),
            (half_l - 24, -half_w),
            (half_l, -half_w * 0.20),
            (half_l, half_w * 0.20),
            (half_l - 24, half_w),
            (-half_l + 14, half_w),
            (-half_l, half_w * 0.60),
        ]


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
        key = stats.key if stats else None
        verts = pen_silhouette_vertices(self.length, self.width, key)
        moment = pymunk.moment_for_poly(mass, verts)
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.body.angle = angle
        self.shape = pymunk.Poly(self.body, verts)
        self.shape.elasticity = stats.elasticity if stats else PEN_ELASTICITY
        self.shape.friction = stats.friction if stats else PEN_FRICTION
        space.add(self.body, self.shape)

        self.color = color
        self.hp = stats.hp if stats else PEN_START_HP
        self.removed = False  # True once the pen has fallen off and left the physics space

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
        self.impacts = []

        def _on_impact(arbiter, space, data):
            pts = arbiter.contact_point_set.points
            if pts:
                pt = pts[0].point_a
                if not any((pt - imp["pos"]).length < 18 for imp in self.impacts):
                    impulse = arbiter.total_impulse.length
                    self.impacts.append({
                        "pos": pymunk.Vec2d(pt.x, pt.y),
                        "life": 0.22,
                        "max_life": 0.22,
                        "impulse": impulse,
                        "sound_played": False,
                    })
            return True

        self.space.on_collision(post_solve=_on_impact)

    def add_pen(
        self, position: tuple, angle: float, color: tuple, stats: Optional[PenStats] = None
    ) -> Pen:
        pen = Pen(self.space, position, angle, color, stats)
        self.pens.append(pen)
        return pen

    def remove_pen(self, pen: Pen) -> None:
        """Take a fallen pen out of the physics space. It stays in self.pens so indexes stay put."""
        if not pen.removed:
            self.space.remove(pen.body, pen.shape)
            pen.removed = True

    def step(self, dt: float) -> None:
        """Advance the simulation by dt seconds using small fixed substeps."""
        dt = min(dt, 1 / 30)  # avoid huge jumps after a lag spike
        h = dt / PHYSICS_SUBSTEPS
        # The space damping slows sliding AND spin by PHYSICS_DAMPING. Spin should fade more
        # slowly (ANGULAR_DAMPING), so after each substep we give back the difference.
        # (Doing this here, not in a Python callback inside pymunk, keeps the game fast.)
        spin_boost = (ANGULAR_DAMPING / PHYSICS_DAMPING) ** h
        spin_slowdown = SPIN_FRICTION * h
        for _ in range(PHYSICS_SUBSTEPS):
            self.space.step(h)
            for pen in self.pens:
                if not pen.removed:
                    spin = pen.body.angular_velocity * spin_boost
                    # Real friction stops a spinning pen quickly and for good, it does not
                    # let the spin fade away slowly. So the spin loses a fixed amount each
                    # moment, and stops dead once it reaches zero.
                    if abs(spin) <= spin_slowdown:
                        spin = 0.0
                    else:
                        spin -= spin_slowdown if spin > 0 else -spin_slowdown
                    pen.body.angular_velocity = spin

        for imp in self.impacts:
            imp["life"] -= dt
        self.impacts = [imp for imp in self.impacts if imp["life"] > 0]

    def is_settled(self) -> bool:
        """True when every pen has (almost) stopped moving and spinning."""
        for pen in self.pens:
            if pen.removed:
                continue
            if pen.body.velocity.length > SETTLE_SPEED:
                return False
            if abs(pen.body.angular_velocity) > SETTLE_ANGULAR_SPEED:
                return False
        return True

    def stop_all(self) -> None:
        """Zero out all motion so tiny leftover drift does not continue."""
        for pen in self.pens:
            if pen.removed:
                continue
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