"""Team matches (2v2 and 3v3)."""

import math
import random

import pytest

from common.constants import (
    ROUND_TURN_LIMIT,
    SUDDEN_DEATH_TURN_LIMIT,
    TEAM_SUDDEN_DEATH_BONUS,
    TEAM_TURN_LIMIT_BONUS,
)
from game.ai import AIPlayer
from game.match import Match
from game.physics import PenWorld

DT = 1 / 60
PENS_2V2 = ("ball_pen", "gel_pen", "marker", "pencil")          # team 0 = first two, team 1 = last two
PENS_3V3 = ("ball_pen", "gel_pen", "marker", "pencil", "fountain_pen", "highlighter")


def settle(m, frames=200):
    for _ in range(frames):
        m.step(DT)


def knock_off(m, *indexes):
    """Put the given pens far outside the board and let the falls finish."""
    for i in indexes:
        m.world.pens[i].body.position = (-500, -500 - 50 * i)
    settle(m)


def skip_until_round_over(m):
    guard = 0
    while not m.round_over:
        if m.can_shoot:
            m.skip_turn()
        else:
            m.step(DT)
        guard += 1
        assert guard < 8000
    settle(m, 5)


# ----- setup -----

@pytest.mark.parametrize("keys,size", [(PENS_2V2, 2), (PENS_3V3, 3)])
def test_team_match_has_the_right_pens(keys, size):
    m = Match(keys)
    assert m.team_size == size
    assert m.mode == "team"
    assert len(m.world.pens) == 2 * size
    assert [m.team_of(i) for i in range(2 * size)] == [0] * size + [1] * size
    assert [p.stats.key for p in m.world.pens] == list(keys)


def test_one_v_one_is_unchanged():
    m = Match(("ball_pen", "marker"))
    assert m.team_size == 1 and m.mode == "pvp"
    assert len(m.world.pens) == 2


@pytest.mark.parametrize("keys", [PENS_2V2, PENS_3V3])
@pytest.mark.parametrize("sudden_death", [False, True])
def test_pens_start_inside_the_board_and_apart(keys, sudden_death):
    m = Match(keys)
    m.sudden_death_next = sudden_death
    m.reset_round()
    board = m.board.as_tuple()
    pens = m.world.pens
    for pen in pens:
        assert PenWorld.edge_distance(pen, board) > 20
    for a in range(len(pens)):
        for b in range(a + 1, len(pens)):
            # Pens start side by side or facing each other, never touching
            dx = abs(pens[a].body.position.x - pens[b].body.position.x)
            dy = abs(pens[a].body.position.y - pens[b].body.position.y)
            gap_x = dx - (pens[a].length + pens[b].length) / 2
            gap_y = dy - (pens[a].width + pens[b].width) / 2
            assert gap_x > 0 or gap_y > 0


def test_teams_face_each_other():
    m = Match(PENS_2V2)
    assert all(math.cos(m.world.pens[i].body.angle) > 0 for i in (0, 1))
    assert all(math.cos(m.world.pens[i].body.angle) < 0 for i in (2, 3))
    assert m.world.pens[0].body.position.x < m.world.pens[2].body.position.x


def test_wrong_number_of_pen_keys_is_fixed_up():
    m = Match(("pencil",) * 3, team_size=2)
    assert len(m.pen_keys) == 4


def test_turn_limits_grow_with_team_size():
    assert Match(PENS_2V2).turn_limit == ROUND_TURN_LIMIT + TEAM_TURN_LIMIT_BONUS
    assert Match(PENS_3V3).turn_limit == ROUND_TURN_LIMIT + 2 * TEAM_TURN_LIMIT_BONUS
    m = Match(PENS_3V3)
    m.sudden_death_next = True
    m.reset_round()
    assert m.turn_limit == SUDDEN_DEATH_TURN_LIMIT + 2 * TEAM_SUDDEN_DEATH_BONUS


# ----- shooting: any pen of your team -----

def test_you_can_flick_any_pen_of_your_team():
    for chosen in (0, 1):
        m = Match(PENS_2V2)
        assert m.current == 0
        assert m.shoot((0, -1), 0.6, pen_index=chosen)
        assert m.shot_pen == chosen
        assert m.active_pen is m.world.pens[chosen]
        other = 1 - chosen
        assert m.world.pens[chosen].body.velocity.length > 0
        assert m.world.pens[other].body.velocity.length == 0


def test_you_cannot_flick_the_other_teams_pen():
    m = Match(PENS_2V2)
    assert not m.shoot((0, -1), 0.6, pen_index=2)
    assert m.can_shoot and m.shots == [0, 0]


def test_without_a_choice_the_first_pen_of_the_team_is_used():
    m = Match(PENS_2V2)
    m.shoot((0, -1), 0.6)
    assert m.shot_pen == 0


def test_teams_take_turns():
    m = Match(PENS_2V2)
    m.shoot((0, -1), 0.3, pen_index=1)
    settle(m, 600)
    assert m.current == 1 and m.can_shoot
    assert m.shoot((0, 1), 0.3, pen_index=3)
    settle(m, 600)
    assert m.current == 0
    assert m.shots == [1, 1]


# ----- falling -----

def test_losing_one_pen_does_not_end_the_round():
    m = Match(PENS_2V2)
    knock_off(m, 2)
    assert not m.round_over
    assert m.fallen == [2]
    assert m.world.pens[2].removed
    assert m.alive_indexes(1) == [3]
    assert m.can_shoot


def test_a_fallen_pen_cannot_be_flicked():
    m = Match(PENS_2V2)
    knock_off(m, 0)
    assert m.alive_indexes(0) == [1]
    assert not m.shoot((0, -1), 0.5, pen_index=0)
    assert m.shoot((0, -1), 0.5)            # default = the pen still on the board
    assert m.shot_pen == 1


def test_the_turn_still_passes_after_a_pen_fell_in_a_shot():
    m = Match(PENS_2V2)
    m.shoot((1, 0), 0.5, pen_index=0)
    m.world.pens[2].body.position = (-500, -500)  # an enemy pen is knocked off during the shot
    settle(m, 600)
    assert not m.round_over
    assert m.current == 1
    assert m.can_shoot


def test_team_with_no_pens_left_loses_the_round():
    m = Match(PENS_2V2)
    knock_off(m, 2)
    assert not m.round_over
    knock_off(m, 3)
    assert m.round_over and m.round_result_applied
    assert m.round_winner == 0
    assert m.scores == [1, 0]
    assert m.last_result == "win"


def test_three_v_three_needs_all_three_to_fall():
    m = Match(PENS_3V3)
    knock_off(m, 3, 4)
    assert not m.round_over
    knock_off(m, 5)
    assert m.round_winner == 0


def test_both_teams_losing_everything_together_is_a_draw():
    m = Match(PENS_2V2)
    for i in range(4):
        m.world.pens[i].body.position = (-500, -500 - 60 * i)
    settle(m)
    assert m.round_result_applied
    assert m.round_winner is None
    assert m.last_result == "draw_replay"


def test_fallen_pens_do_not_block_the_other_pens():
    """A pen that fell is out of the physics space, so it cannot be hit from off the board."""
    m = Match(PENS_2V2)
    knock_off(m, 2)
    ghost = m.world.pens[2]
    assert ghost.body.space is None
    assert m.world.is_settled()


# ----- turn limit -----

def test_turn_limit_with_more_pens_left_wins_the_round():
    m = Match(PENS_2V2)
    knock_off(m, 2)          # team 1 is down to one pen, team 0 has two
    skip_until_round_over(m)
    assert m.draw_by_limit
    assert m.turns_taken == [m.turn_limit, m.turn_limit]
    assert m.round_winner == 0
    assert m.last_result == "win"
    assert m.scores == [1, 0]


def test_turn_limit_with_equal_pens_is_a_draw():
    m = Match(PENS_2V2)
    skip_until_round_over(m)
    assert m.draw_by_limit
    assert m.round_winner is None
    assert m.last_result == "draw_replay"


def test_team_sudden_death_draw_goes_to_the_team_nearer_the_middle():
    m = Match(PENS_2V2)
    m.sudden_death_next = True
    m.reset_round()
    x, y, w, h = m.board.as_tuple()
    for i in (0, 1):  # team 0 sits in the middle, team 1 near the edge
        m.world.pens[i].body.position = (x + w / 2 - 10, y + h / 2 + (i - 0.5) * 60)
    for i in (2, 3):
        m.world.pens[i].body.position = (x + 30, y + h / 2 + (i - 2.5) * 60)
    skip_until_round_over(m)
    assert m.last_result == "draw_decided"
    assert m.round_winner == 0


def test_a_team_match_can_be_won():
    m = Match(PENS_2V2)
    knock_off(m, 2, 3)
    m.next_round()
    knock_off(m, 2, 3)
    assert m.match_winner == 0


# ----- save / load -----

def test_team_state_round_trip():
    m = Match(PENS_3V3, mode="team")
    knock_off(m, 3, 4, 5)
    m.next_round()
    state = m.to_state()
    assert state["team_size"] == 3
    back = Match.from_state(state)
    assert back.team_size == 3 and back.mode == "team"
    assert back.pen_keys == list(PENS_3V3)
    assert back.scores == [1, 0]
    assert len(back.world.pens) == 6


def test_old_save_without_team_size_loads_as_one_v_one():
    old = {"mode": "pvp", "pens": ["pencil", "marker"], "score": [1, 0], "round": 2}
    m = Match.from_state(old)
    assert m.team_size == 1
    assert m.pen_keys == ["pencil", "marker"]


@pytest.mark.parametrize("bad", [
    {"team_size": 2, "pens": ["pencil", "marker"]},          # too few pens for 2v2
    {"team_size": 9, "pens": 5},
    {"team_size": "x", "pens": None},
    {"team_size": -4},
])
def test_bad_team_save_still_loads(bad):
    m = Match.from_state(bad)
    assert 1 <= m.team_size <= 3
    assert len(m.pen_keys) == 2 * m.team_size
    assert m.can_shoot


# ----- computer -----

def test_the_computer_does_not_play_team_matches():
    with pytest.raises(ValueError):
        AIPlayer("easy", random.Random(1)).choose_shot(Match(PENS_2V2))
