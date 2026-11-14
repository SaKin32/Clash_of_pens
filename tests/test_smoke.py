"""Basic checks that run in CI."""

from common.pen import PENS
from game.physics import PenWorld


def test_six_pens():
    assert len(PENS) == 6


def test_pen_world_runs():
    world = PenWorld()
    world.add_pen((400, 300), 0.0, (255, 0, 0), PENS[0])
    world.add_pen((800, 300), 3.14, (0, 0, 255), PENS[1])
    world.step(1 / 60)
    assert len(world.pens) == 2