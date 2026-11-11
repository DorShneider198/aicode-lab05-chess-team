"""Redo with captured pieces, promotion, save/load and new game."""

import json

import pytest

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


PAWN_TRADE = [("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5")]


def promoted_game():
    session = Session()
    act(session, "promotion-setup")
    act(session, "move", source="b7", target="a8", promotion="N")
    return session


def test_redo_of_a_capture_updates_the_captured_display():
    session = Session()
    play_moves(session, *PAWN_TRADE[:3])
    act(session, "undo")
    assert session.view()["captured"] == []
    view = act(session, "redo")
    assert view["captured"] == ["bP"]
    assert session.position[0]["d5"] == "wP"
    assert view["moves"][-1] == "e4xd5"


def test_redo_of_a_promotion_brings_back_the_same_piece():
    session = promoted_game()
    act(session, "undo")
    assert session.position[0]["b7"] == "wP"
    view = act(session, "redo")
    assert session.position[0]["a8"] == "wN"  # the knight chosen, not a queen
    assert view["moves"][-1].startswith("b7xa8=N")
    assert view["captured"] == ["bP", "bR", "wP"]


def test_redo_against_the_computer_restores_its_capture():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    session.play("d7", "d5")  # Black's reply chosen for the test
    play_moves(session, ("e4", "d5"))
    act(session, "computer-move")  # the queen recaptures: d8xd5
    after = session.view()
    act(session, "undo")
    # Your capture and the computer's recapture are both undone.
    assert session.view()["captured"] == []
    view = act(session, "redo")
    assert view == after
    assert view["captured"] == ["bP", "wP"]


def test_save_and_load_preserve_redo(save_file):
    session = Session()
    play_moves(session, *PAWN_TRADE)
    act(session, "undo")
    act(session, "undo")
    act(session, "save")
    data = json.loads(save_file.read_text())
    assert data["moves"] == [["e2", "e4"], ["d7", "d5"]]
    assert data["redo"] == [["e4", "d5"], ["d8", "d5"]]

    fresh = Session()
    view = act(fresh, "load")
    assert view["moves"] == ["e2-e4", "d7-d5"]
    assert view["can_redo"] is True
    act(fresh, "redo")
    view = act(fresh, "redo")
    assert view["moves"] == ["e2-e4", "d7-d5", "e4xd5", "d8xd5"]
    assert view["captured"] == ["bP", "wP"]


def test_redo_of_a_promotion_after_save_and_load():
    session = promoted_game()
    act(session, "undo")
    act(session, "save")
    fresh = Session()
    act(fresh, "load")
    act(fresh, "redo")
    assert fresh.position[0]["a8"] == "wN"


def test_redo_against_the_computer_after_save_and_load():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    act(session, "computer-move")
    after = session.view()
    act(session, "undo")
    act(session, "save")
    fresh = Session()
    act(fresh, "load")
    assert fresh.opponent == "computer"
    assert act(fresh, "redo") == after


def test_save_without_redo_has_no_redo_list(save_file):
    session = Session()
    play_moves(session, ("e2", "e4"))
    act(session, "save")
    assert "redo" not in json.loads(save_file.read_text())


def test_a_new_move_after_load_discards_the_loaded_redo():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    act(session, "undo")
    act(session, "save")
    fresh = Session()
    act(fresh, "load")
    view = act(fresh, "move", source="c7", target="c5")
    assert view["can_redo"] is False
    assert fresh.notation == ["e2-e4", "c7-c5"]


def test_new_game_after_load_clears_redo():
    session = Session()
    play_moves(session, ("e2", "e4"))
    act(session, "undo")
    act(session, "save")
    fresh = Session()
    act(fresh, "load")
    assert act(fresh, "new", opponent="human")["can_redo"] is False


@pytest.mark.parametrize("redo", ["e4", [["e7", "e5"]], [["e2"]]])
def test_bad_redo_list_in_save_file_is_rejected(save_file, redo):
    save_file.write_text(
        json.dumps({"version": 1, "opponent": "human", "moves": [], "redo": redo})
    )
    session = Session()
    play_moves(session, ("d2", "d4"))
    before = session.view()
    with pytest.raises((ValueError, TypeError)):
        act(session, "load")
    assert session.view() == before
