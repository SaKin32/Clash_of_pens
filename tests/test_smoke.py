"""Basic checks that run in CI."""

from common.pen import PENS
from game.physics import PenWorld


def _all_pens():
    return list(PENS.values()) if isinstance(PENS, dict) else list(PENS)


def test_six_pens():
    assert len(_all_pens()) == 6


def test_pen_world_runs():
    pens = _all_pens()
    world = PenWorld()
    world.add_pen((400, 300), 0.0, (255, 0, 0), pens[0])
    world.add_pen((800, 300), 3.14, (0, 0, 255), pens[1])
    world.step(1 / 60)
    assert len(world.pens) == 2