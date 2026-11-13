import math
import random

import pytest

from common.constants import AI_MIN_POWER
from game.ai import DEFAULT_DIFFICULTY, DIFFICULTIES, PROFILES, AIPlayer, Shot
from game.match import Match

DT = 1 / 60


def test_three_difficulties():
    assert DIFFICULTIES == ("easy", "medium", "hard")


def test_unknown_difficulty_falls_back_to_default():
    assert AIPlayer("impossible").difficulty == DEFAULT_DIFFICULTY


def test_harder_levels_make_smaller_aiming_errors():
    errors = [PROFILES[d].aim_noise for d in DIFFICULTIES]
    assert errors == sorted(errors, reverse=True)
    assert PROFILES["easy"].candidates == 0
    assert PROFILES["medium"].candidates < PROFILES["hard"].candidates


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("pens", [("ball_pen", "marker"), ("pencil", "gel_pen")])
def test_shot_is_valid_for_every_difficulty(difficulty, pens):
    ai = AIPlayer(difficulty, random.Random(1))
    m = Match(pens)
    for _ in range(10):
        shot = ai.choose_shot(m)
        assert isinstance(shot, Shot)
        assert AI_MIN_POWER <= shot.power <= 1.0
        assert math.isfinite(shot.angle)
        assert shot.direction.length == pytest.approx(1.0)


def test_same_seed_gives_same_shot():
    m = Match()
    a = AIPlayer("hard", random.Random(42)).choose_shot(m)
    b = AIPlayer("hard", random.Random(42)).choose_shot(m)
    assert a == b


def test_ai_plays_either_side():
    m = Match(("ball_pen", "gel_pen"))
    ai = AIPlayer("medium", random.Random(5))
    for _ in range(2):  # first as player 1, then as player 2
        shot = ai.choose_shot(m)
        assert m.shoot(shot.direction, shot.power)
        for _ in range(600):
            m.step(DT)
            if m.can_shoot:
                break


def test_easy_usually_aims_toward_the_opponent():
    m = Match()  # opponent is straight ahead, to the right
    ai = AIPlayer("easy", random.Random(7))
    toward = sum(math.cos(ai.choose_shot(m).angle) > 0 for _ in range(200))
    assert toward > 150


def test_hard_picks_a_flick_that_hits_the_opponent():
    """With the opponent within reach, a Hard flick should reach and push it.

    (At the very start the pens are too far apart for any flick to connect, so the
    pens are placed closer here.)
    """
    m = Match()
    x, y, w, h = m.board.as_tuple()
    m.world.pens[0].body.position = (x + w / 2 - 150, y + h / 2)
    m.world.pens[1].body.position = (x + w / 2 + 150, y + h / 2)
    ai = AIPlayer("hard", random.Random(3))
    shot = ai.choose_shot(m)
    opponent_start = m.world.pens[1].body.position
    m.shoot(shot.direction, shot.power)
    for _ in range(300):
        m.step(DT)
    assert m.world.pens[1].body.position.get_distance(opponent_start) > 1.0 or m.round_over


def test_ai_avoids_shooting_itself_off_the_edge():
    """Hard sitting right at its own edge, facing the opponent, must not fire off the board."""
    m = Match()
    x, y, w, h = m.board.as_tuple()
    m.world.pens[0].body.position = (x + 30, y + h / 2)
    ai = AIPlayer("hard", random.Random(11))
    shot = ai.choose_shot(m)
    m.shoot(shot.direction, shot.power)
    for _ in range(300):
        m.step(DT)
    assert 0 not in m.falling


def test_ai_takes_a_winning_shot_when_one_exists():
    """Opponent hanging on the edge: Hard should be able to push it off."""
    wins = 0
    for seed in range(5):
        m = Match()
        x, y, w, h = m.board.as_tuple()
        m.world.pens[0].body.position = (x + w - 260, y + h / 2)
        m.world.pens[1].body.position = (x + w - 60, y + h / 2)
        ai = AIPlayer("hard", random.Random(seed))
        shot = ai.choose_shot(m)
        m.shoot(shot.direction, shot.power)
        for _ in range(400):
            m.step(DT)
        wins += m.round_winner == 0
    assert wins >= 3
