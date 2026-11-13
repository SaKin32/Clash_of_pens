"""AI-versus-AI checks.

The difficulty-order test runs by default. The pen balance test is slow (about a minute),
so run it on purpose:   pytest -m balance
"""

import itertools

import pytest

from common.pen import PEN_ORDER
from game.headless import play_match, win_rate


def _wins(strong, weak, matches):
    wins = 0
    for n in range(matches):
        if n % 2 == 0:
            wins += play_match(("ball_pen", "ball_pen"), (strong, weak), seed=n).winner == 0
        else:
            wins += play_match(("ball_pen", "ball_pen"), (weak, strong), seed=n).winner == 1
    return wins


def test_a_match_always_finishes_with_a_valid_result():
    for seed in range(4):
        r = play_match(("marker", "pencil"), ("medium", "medium"), seed=seed)
        assert r.winner in (0, 1)
        assert max(r.scores) == 2
        assert r.rounds >= 2


def test_medium_beats_easy():
    assert _wins("medium", "easy", 8) >= 7


def test_hard_beats_easy():
    assert _wins("hard", "easy", 8) >= 7


def test_hard_beats_medium_more_often_than_not():
    assert _wins("hard", "medium", 12) >= 6


@pytest.mark.balance
def test_no_pen_is_much_stronger_or_weaker_than_the_rest():
    matches = 14
    totals = {k: 0.0 for k in PEN_ORDER}
    for a, b in itertools.combinations(PEN_ORDER, 2):
        rate = win_rate(a, b, "medium", matches)
        totals[a] += rate
        totals[b] += 1 - rate
    for pen, total in totals.items():
        average = total / (len(PEN_ORDER) - 1)
        assert 0.25 <= average <= 0.75, f"{pen} wins {average:.0%} of its matches"
