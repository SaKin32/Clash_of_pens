"""The six pens: stats for each one.

Every stat is a plain number so the physics, the pen select screen and the AI can
all read the same data. To rebalance the game, change the numbers here.

    mass        heavier pens push lighter pens around in a collision
    length      pen length in pixels (longer = bigger target and reach)
    width       pen thickness in pixels. Keep length/width close to the shape of the
                pen picture so the picture is never stretched and always fits its hitbox.
                Gel, Fountain and Metal pens share the same length on purpose. The Ball Pen
                is a little longer and thicker because its picture is very thin.
    elasticity  bounciness of a hit (0 = dead, 1 = perfect bounce)
    friction    grip between two touching pens
    power       multiplier on the shot speed (1.0 = standard flick)
    hp          starting health (stored for the HP system, not used by the rules yet)
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


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
        mass=3.0, length=255, width=20,
        elasticity=0.9, friction=0.24, power=1.0, hp=100,
        color=(70, 130, 220),
    ),
    "gel_pen": PenStats(
        key="gel_pen",
        name="Gel Pen",
        description="Light and fast, bounces off hits.",
        mass=2.6, length=255, width=23,
        elasticity=0.95, friction=0.18, power=1.2, hp=90,
        color=(150, 100, 220),
    ),
    "fountain_pen": PenStats(
        key="fountain_pen",
        name="Fountain Pen",
        description="Long and heavy, slower to launch.",
        mass=3.3, length=255, width=23,
        elasticity=0.8, friction=0.27, power=0.9, hp=110,
        color=(200, 170, 60),
    ),
    "marker": PenStats(
        key="marker",
        name="Marker",
        description="Thick and very heavy. Hard to push.",
        mass=3.4, length=240, width=29,
        elasticity=0.78, friction=0.3, power=0.95, hp=120,
        color=(80, 180, 110),
    ),
    "metal_pen": PenStats(
        key="metal_pen",
        name="Metal Pen",
        description="Steel barrel with lively rebounds.",
        mass=3.05, length=255, width=28,
        elasticity=0.93, friction=0.2, power=1.02, hp=105,
        color=(160, 172, 190),
    ),
    "highlighter": PenStats(
        key="highlighter",
        name="Highlighter",
        description="Wide body with steady grip.",
        mass=3.2, length=200, width=54,
        elasticity=0.85, friction=0.27, power=1.0, hp=100,
        color=(230, 120, 190),
    ),
}

PEN_ORDER: List[str] = list(PENS.keys())
DEFAULT_PEN_KEY = "ball_pen"

# Old pen keys from earlier versions, so old save files still load the right pen.
LEGACY_KEYS: Dict[str, str] = {"pencil": "metal_pen"}


def get_pen(key: str) -> PenStats:
    """Return the stats for a pen key. Unknown keys fall back to the default pen."""
    key = LEGACY_KEYS.get(key, key)
    return PENS.get(key, PENS[DEFAULT_PEN_KEY])


# What the pen is like in real life, shown on the pen select screen (approximate values).
# Each entry is (label, value). Keep the labels the same for every pen so the screen lines up.
PEN_FACTS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "ball_pen": (
        ("Made of", "Light plastic barrel"),
        ("Weight", "about 5 g"),
        ("Length", "about 15 cm"),
        ("Ink", "Thick oil-based ink"),
        ("Strength", "Tough enough for daily use"),
    ),
    "gel_pen": (
        ("Made of", "Plastic with a rubber grip"),
        ("Weight", "about 12 g"),
        ("Length", "about 14 cm"),
        ("Ink", "Smooth water-based gel ink"),
        ("Strength", "Light and quick, but not heavy"),
    ),
    "fountain_pen": (
        ("Made of", "Metal and resin body"),
        ("Weight", "about 28 g"),
        ("Length", "about 14 cm"),
        ("Ink", "Liquid ink through a steel nib"),
        ("Strength", "Heavy and balanced, slow to start"),
    ),
    "marker": (
        ("Made of", "Thick plastic barrel"),
        ("Weight", "about 22 g"),
        ("Length", "about 13 cm"),
        ("Ink", "Alcohol ink, felt tip"),
        ("Strength", "Short, wide and very hard to push"),
    ),
    "metal_pen": (
        ("Made of", "Solid steel barrel"),
        ("Weight", "about 26 g"),
        ("Length", "about 14 cm"),
        ("Ink", "Ball tip with a metal refill"),
        ("Strength", "Hard and springy, rebounds well"),
    ),
    "highlighter": (
        ("Made of", "Wide plastic body"),
        ("Weight", "about 14 g"),
        ("Length", "about 12 cm"),
        ("Ink", "Bright ink, flat chisel tip"),
        ("Strength", "Wide body with a steady grip"),
    ),
}


def get_facts(key: str) -> Tuple[Tuple[str, str], ...]:
    """Real-life facts for a pen key (same fallback rules as get_pen)."""
    return PEN_FACTS[get_pen(key).key]