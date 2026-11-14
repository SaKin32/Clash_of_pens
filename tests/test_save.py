import json
import os

from game import save
from game.match import Match


def test_no_save_at_first(save_dir):
    assert not save.has_save()
    assert save.load_game() is None


def test_save_and_load_a_match(save_dir):
    m = Match(("pencil", "gel_pen"), mode="pvc", difficulty="easy")
    assert save.save_game(m.to_state())
    assert save.has_save()
    back = Match.from_state(save.load_game())
    assert back.pen_keys == ["pencil", "gel_pen"]
    assert back.difficulty == "easy"


def test_corrupt_file_means_no_save(save_dir):
    with open(save.save_path(), "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    assert save.load_game() is None
    assert not save.has_save()


def test_wrong_version_or_shape_is_ignored(save_dir):
    for data in (
        {"version": 999, "state": {"mode": "pvp"}},
        {"version": 1, "state": "nope"},
        {"version": 1, "state": {"mode": "online"}},
        ["list"],
    ):
        with open(save.save_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
        assert save.load_game() is None


def test_delete_save(save_dir):
    save.save_game(Match().to_state())
    save.delete_save()
    assert not save.has_save()
    save.delete_save()  # deleting twice is fine


def test_save_leaves_no_temp_file(save_dir):
    save.save_game(Match().to_state())
    assert not os.path.exists(save.save_path() + ".tmp")


def test_team_match_can_be_saved_and_resumed(save_dir):
    keys = ("ball_pen", "gel_pen", "marker", "pencil", "fountain_pen", "highlighter")
    m = Match(keys, mode="team")
    assert save.save_game(m.to_state())
    assert save.has_save()
    back = Match.from_state(save.load_game())
    assert back.mode == "team"
    assert back.team_size == 3
    assert back.pen_keys == list(keys)
