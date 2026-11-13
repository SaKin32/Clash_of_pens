import math

import pytest

from common.constants import (
    ROUND_TURN_LIMIT,
    ROUNDS_TO_WIN,
    SUDDEN_DEATH_BOARD_SIZE,
    SUDDEN_DEATH_TURN_LIMIT,
    TURN_TIME_LIMIT,
)
from game.match import Match
from game.physics import PenWorld

DT = 1 / 60


def settle(match, frames=400):
    for _ in range(frames):
        match.step(DT)


def knock_off(match, loser):
    """Put one pen far outside the board and let the fall finish."""
    match.world.pens[loser].body.position = (-500, -500)
    settle(match)


def finish_round_with_draw(match):
    """Skip turns until the turn limit ends the round."""
    guard = 0
    while not match.round_over:
        if match.can_shoot:
            match.skip_turn()
        else:
            match.step(DT)
        guard += 1
        assert guard < 5000, "round never ended"
    settle(match, 5)


def test_new_match_starts_clean():
    m = Match(("ball_pen", "marker"))
    assert m.scores == [0, 0]
    assert m.round_number == 1
    assert m.match_winner is None
    assert m.can_shoot
    assert m.world.pens[1].stats.key == "marker"


def test_pens_use_their_own_stats():
    m = Match(("pencil", "marker"))
    a, b = m.world.pens
    assert a.length != b.length
    assert a.body.mass != b.body.mass or a.width != b.width


def test_shoot_moves_pen_and_counts_the_shot():
    m = Match()
    assert m.shoot((1, 0), 0.8)
    assert m.shots == [1, 0]
    assert m.turns_taken == [1, 0]
    assert m.world.pens[0].body.velocity.x > 0
    assert not m.can_shoot  # shot in flight


def test_shoot_rejects_zero_direction_and_second_shot():
    m = Match()
    assert not m.shoot((0, 0), 1.0)
    assert m.shoot((1, 0), 0.5)
    assert not m.shoot((1, 0), 0.5)


def test_turn_passes_after_pens_settle():
    m = Match()
    m.shoot((0, 1), 0.3)
    settle(m, 600)
    assert m.current == 1
    assert m.turn_id == 1
    assert m.can_shoot


def test_turn_timer_skips_the_turn():
    m = Match()
    for _ in range(int((TURN_TIME_LIMIT + 1) / DT)):
        m.step(DT)
        if m.turn_id:
            break
    assert m.turn_id == 1
    assert m.current == 1
    assert m.turns_taken == [1, 0]
    assert m.shots == [0, 0]
    assert m.turn_time_left > TURN_TIME_LIMIT - 1


def test_falling_off_loses_the_round():
    m = Match()
    knock_off(m, loser=1)
    assert m.round_over and m.round_result_applied
    assert m.round_winner == 0
    assert m.scores == [1, 0]
    assert m.last_result == "win"
    assert m.match_winner is None
    assert not m.can_shoot


def test_first_to_two_rounds_wins_the_match():
    m = Match()
    knock_off(m, loser=1)
    assert m.next_round()
    assert m.round_number == 2
    knock_off(m, loser=1)
    assert m.scores == [ROUNDS_TO_WIN, 0]
    assert m.match_winner == 0
    assert not m.next_round()  # the match is over


def test_match_can_go_to_three_rounds():
    m = Match()
    knock_off(m, loser=1)
    m.next_round()
    knock_off(m, loser=0)
    assert m.scores == [1, 1] and m.match_winner is None
    m.next_round()
    knock_off(m, loser=0)
    assert m.match_winner == 1


def test_next_round_not_allowed_before_result():
    m = Match()
    assert not m.next_round()


def test_players_take_turns_shooting_first():
    m = Match()
    assert m.starter == 0
    knock_off(m, loser=1)
    m.next_round()
    assert m.starter == 1 and m.current == 1


def test_both_pens_falling_is_a_draw_that_replays():
    m = Match()
    m.world.pens[0].body.position = (-500, -500)
    m.world.pens[1].body.position = (-600, -500)
    settle(m)
    assert m.round_result_applied
    assert m.round_winner is None
    assert m.last_result == "draw_replay"
    assert m.scores == [0, 0]
    assert m.round_number == 1
    m.next_round()
    assert not m.sudden_death


def test_turn_limit_ends_the_round_in_a_draw():
    m = Match()
    finish_round_with_draw(m)
    assert m.draw_by_limit
    assert m.turns_taken == [ROUND_TURN_LIMIT, ROUND_TURN_LIMIT]
    assert m.last_result == "draw_replay"


def test_second_draw_goes_to_sudden_death_on_a_small_board():
    m = Match()
    finish_round_with_draw(m)
    assert m.last_result == "draw_replay"
    m.next_round()
    finish_round_with_draw(m)
    assert m.last_result == "sudden_death"
    assert m.round_winner is None
    assert m.scores == [0, 0]

    m.next_round()
    assert m.sudden_death
    assert m.turn_limit == SUDDEN_DEATH_TURN_LIMIT
    _, _, w, h = m.board.as_tuple()
    assert (w, h) == SUDDEN_DEATH_BOARD_SIZE
    a, b = m.world.pens
    # Both pens start inside the small board and do not overlap
    for pen in (a, b):
        assert PenWorld.edge_distance(pen, m.board.as_tuple()) > 0
    gap = b.body.position.x - a.body.position.x - (a.length + b.length) / 2
    assert gap > 0


def test_sudden_death_never_shrinks_the_board_again():
    m = Match()
    m.sudden_death_next = True
    m.reset_round()
    before = m.board.as_tuple()
    for _ in range(SUDDEN_DEATH_TURN_LIMIT - 1):
        while not m.can_shoot:
            m.step(DT)
        m.skip_turn()
        m.skip_turn()
    assert m.board.target is None
    assert m.board.as_tuple() == before


def test_sudden_death_fall_wins_a_point():
    m = Match()
    m.sudden_death_next = True
    m.reset_round()
    knock_off(m, loser=0)
    assert m.last_result == "win"
    assert m.round_winner == 1
    assert m.scores == [0, 1]


def test_sudden_death_draw_is_decided_by_the_middle():
    m = Match()
    m.sudden_death_next = True
    m.reset_round()
    x, y, w, h = m.board.as_tuple()
    m.world.pens[0].body.position = (x + w / 2, y + h / 2)  # dead centre
    m.world.pens[1].body.position = (x + 40, y + h / 2)     # near the edge
    finish_round_with_draw(m)
    assert m.last_result == "draw_decided"
    assert m.round_winner == 0
    assert m.scores == [1, 0]


def test_board_warns_then_shrinks_before_the_turn_limit():
    m = Match()
    start_width = m.board.as_tuple()[2]
    warned = False
    guard = 0
    while not m.round_over and guard < 5000:
        if m.can_shoot:
            m.skip_turn()
            warned = warned or m.board.target is not None
        else:
            m.step(DT)
        guard += 1
    assert warned
    assert m.board.shrink_count >= 1
    assert m.board.as_tuple()[2] < start_width


def test_no_shots_after_the_round_is_over():
    m = Match()
    knock_off(m, loser=1)
    assert not m.shoot((1, 0), 1.0)


def test_state_round_trip():
    m = Match(("gel_pen", "marker"), mode="pvc", difficulty="hard")
    knock_off(m, loser=1)
    m.next_round()
    state = m.to_state()
    assert state["mode"] == "pvc"
    assert state["score"] == [1, 0]

    back = Match.from_state(state)
    assert back.pen_keys == ["gel_pen", "marker"]
    assert back.mode == "pvc" and back.difficulty == "hard"
    assert back.scores == [1, 0]
    assert back.round_number == 2
    assert back.starter == m.starter  # the round in progress restarts with the same starter
    assert back.can_shoot


def test_saving_in_sudden_death_resumes_in_sudden_death():
    m = Match()
    m.sudden_death_next = True
    m.reset_round()
    back = Match.from_state(m.to_state())
    assert back.sudden_death


def test_from_state_survives_garbage():
    for bad in (
        {},
        {"mode": "pvp", "score": "nope", "pens": 7, "round": "x"},
        {"mode": "pvp", "score": [99, -5], "pens": ["nope", None], "round": -3},
        {"mode": "weird", "difficulty": 12, "draw_replays_used": 50},
    ):
        m = Match.from_state(bad)
        assert m.match_winner is None
        assert all(0 <= s < ROUNDS_TO_WIN for s in m.scores)
        assert m.round_number >= 1
        assert len(m.pen_keys) == 2
        assert m.mode in ("pvc", "pvp")
        assert m.can_shoot
