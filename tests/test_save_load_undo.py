"""Save/load and undo together: behavior neither feature's own tests cover."""

import json

import pytest

from game import new_position
from session import Session


@pytest.fixture(autouse=True)
def save_file(tmp_path, monkeypatch):
    path = tmp_path / "game.save.json"
    monkeypatch.setattr(Session, "save_path", path)
    return path


def act(session, action, **fields):
    return session.dispatch({"action": action, **fields})


def play_moves(session, *moves):
    for source, target in moves:
        act(session, "move", source=source, target=target)


def assert_consistent(session):
    """The move list for saving, the notation and the undo history stay in step."""
    assert len(session.moves) == len(session.notation) == len(session.history)


def save_and_reload(session):
    act(session, "save")
    fresh = Session()
    act(fresh, "load")
    return fresh


def test_moves_made_before_saving_can_be_undone_after_loading():
    first = Session()
    play_moves(first, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    fresh = save_and_reload(first)
    assert fresh.view()["can_undo"] is True
    act(fresh, "undo")
    assert fresh.position[0]["d5"] == "bP"  # captured pawn is back
    assert fresh.position[0]["e4"] == "wP"
    assert fresh.position[1] == "w"
    assert fresh.notation == ["e2-e4", "d7-d5"]
    assert_consistent(fresh)


def test_undo_all_the_way_back_after_loading():
    first = Session()
    play_moves(first, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    fresh = save_and_reload(first)
    for _ in range(5):
        act(fresh, "undo")
    assert fresh.position == new_position()
    assert fresh.view()["can_undo"] is False
    assert_consistent(fresh)


def test_loaded_computer_game_undoes_your_move_and_its_reply():
    first = Session("computer")
    play_moves(first, ("e2", "e4"))
    act(first, "computer-move")
    play_moves(first, ("d2", "d4"))
    act(first, "computer-move")
    earlier = first.notation[:2]
    fresh = save_and_reload(first)
    act(fresh, "undo")
    assert fresh.notation == earlier
    assert fresh.position[1] == "w"
    assert fresh.opponent == "computer"
    assert_consistent(fresh)


def test_loaded_on_computers_turn_undo_takes_back_only_your_move():
    first = Session("computer")
    play_moves(first, ("e2", "e4"))
    fresh = save_and_reload(first)
    assert fresh.computer_to_move()
    act(fresh, "undo")
    assert fresh.position == new_position()
    assert not fresh.computer_to_move()


def test_save_after_undo_stores_the_current_line_only(save_file):
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    act(session, "undo")
    act(session, "save")
    assert json.loads(save_file.read_text())["moves"] == [["e2", "e4"]]
    fresh = Session()
    act(fresh, "load")
    assert fresh.notation == ["e2-e4"]
    assert fresh.position[1] == "b"


def test_save_after_undo_and_a_different_move(save_file):
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    act(session, "undo")
    play_moves(session, ("c7", "c5"))
    fresh = save_and_reload(session)
    assert fresh.notation == ["e2-e4", "c7-c5"]
    assert "e5" not in fresh.position[0]
    assert fresh.position[0]["c5"] == "bP"
    assert_consistent(fresh)


def test_save_after_undoing_everything_loads_a_new_game():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    act(session, "computer-move")
    act(session, "undo")
    fresh = save_and_reload(session)
    assert fresh.position == new_position()
    assert fresh.opponent == "computer"
    assert fresh.view()["can_undo"] is False


def test_load_replaces_the_undo_history_of_the_current_game():
    act(Session(), "save")  # empty saved game
    session = Session()
    play_moves(session, ("d2", "d4"), ("d7", "d5"))
    act(session, "load")
    assert session.view()["can_undo"] is False
    act(session, "undo")
    assert session.position == new_position()  # never back to d4/d5


def test_failed_load_keeps_the_undo_history():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    with pytest.raises(ValueError):
        act(session, "load")  # nothing saved yet
    act(session, "undo")
    assert session.notation == ["e2-e4"]
    assert_consistent(session)


def test_undo_load_undo_sequence_stays_consistent():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"), ("b8", "c6"))
    act(session, "undo")
    act(session, "save")
    play_moves(session, ("g8", "f6"))
    act(session, "load")
    assert session.notation == ["e2-e4", "e7-e5", "g1-f3"]
    act(session, "undo")
    act(session, "undo")
    assert session.notation == ["e2-e4"]
    assert_consistent(session)


def test_undo_after_promotion_setup_then_save_and_load():
    session = Session()
    act(session, "promotion-setup")
    act(session, "undo")
    fresh = save_and_reload(session)
    assert fresh.position[0]["g2"] == "wP"
    assert fresh.position[0]["h3"] == "bP"
    assert len(fresh.notation) == 7
    assert_consistent(fresh)
