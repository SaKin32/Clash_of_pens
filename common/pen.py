"""The six pens: stats for each one.

Every stat is a plain number so the physics, the pen select screen and the AI can
all read the same data. To rebalance the game, change the numbers here.

    mass        heavier pens push lighter pens around in a collision
    length      pen length in pixels (longer = bigger target and reach)
    width       pen thickness in pixels
    elasticity  bounciness of a hit (0 = dead, 1 = perfect bounce)
    friction    grip between two touching pens
    power       multiplier on the shot speed (1.0 = standard flick)
    hp          starting health (stored for the HP system, not used by the rules yet)
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PenStats:
    key: str
    name: str
    description: str
    mass: float
    length: int
    width: int
    elasticity: float
    friction: float
    power: float
    hp: int
    color: tuple


PENS: Dict[str, PenStats] = {
    "ball_pen": PenStats(
        key="ball_pen",
        name="Ball Pen",
        description="Balanced all-rounder.",
        mass=3.0, length=170, width=26,
        elasticity=0.6, friction=0.4, power=1.0, hp=100,
        color=(70, 130, 220),
    ),
    "gel_pen": PenStats(
        key="gel_pen",
        name="Gel Pen",
        description="Light and fast, bounces off hits.",
        mass=2.6, length=165, width=24,
        elasticity=0.7, friction=0.3, power=1.2, hp=90,
        color=(150, 100, 220),
    ),
    "fountain_pen": PenStats(
        key="fountain_pen",
        name="Fountain Pen",
        description="Long and heavy, slower to launch.",
        mass=3.3, length=180, width=24,
        elasticity=0.5, friction=0.45, power=0.9, hp=110,
        color=(200, 170, 60),
    ),
    "marker": PenStats(
        key="marker",
        name="Marker",
        description="Short and very heavy. Hard to push.",
        mass=3.4, length=140, width=37,
        elasticity=0.48, friction=0.5, power=0.95, hp=120,
        color=(80, 180, 110),
    ),
    "pencil": PenStats(
        key="pencil",
        name="Pencil",
        description="Long, thin and light. Big reach.",
        mass=2.55, length=192, width=21,
        elasticity=0.55, friction=0.35, power=1.17, hp=80,
        color=(235, 190, 70),
    ),
    "highlighter": PenStats(
        key="highlighter",
        name="Highlighter",
        description="Wide body with steady grip.",
        mass=3.2, length=155, width=33,
        elasticity=0.55, friction=0.45, power=1.0, hp=100,
        color=(230, 120, 190),
    ),
}

PEN_ORDER: List[str] = list(PENS.keys())
DEFAULT_PEN_KEY = "ball_pen"


def get_pen(key: str) -> PenStats:
    """Return the stats for a pen key. Unknown keys fall back to the default pen."""
    return PENS.get(key, PENS[DEFAULT_PEN_KEY])
