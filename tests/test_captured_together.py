"""Captured pieces working together with undo, save/load, and the computer."""

import pytest

from game import new_position
from session import Session


@pytest.fixture(autouse=True)
def save_file(tmp_path, monkeypatch):
    path = tmp_path / "game.save.json"
    monkeypatch.setattr(Session, "save_path", path)
    return path


def play_moves(session, *moves):
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def captured(session):
    return session.view()["captured"]


# e4xd5 captures a black pawn; Black recaptures with the queen.
PAWN_TRADE = [("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5")]


def test_display_shows_the_type_of_the_captured_piece():
    session = Session()
    play_moves(session, ("g1", "f3"), ("b8", "c6"), ("f3", "e5"), ("c6", "e5"))
    assert captured(session) == ["wN"]


def test_undo_removes_a_capture_from_the_display():
    session = Session()
    play_moves(session, *PAWN_TRADE[:3])
    assert captured(session) == ["bP"]
    view = session.dispatch({"action": "undo"})
    assert view["captured"] == []
    assert session.position[0]["d5"] == "bP"


def test_undo_of_a_quiet_move_keeps_earlier_captures():
    session = Session()
    play_moves(session, *PAWN_TRADE[:3], ("g8", "f6"))
    session.dispatch({"action": "undo"})
    assert captured(session) == ["bP"]


def test_repeated_undo_empties_the_display():
    session = Session()
    play_moves(session, *PAWN_TRADE)
    assert captured(session) == ["bP", "wP"]
    session.dispatch({"action": "undo"})
    assert captured(session) == ["bP"]
    for _ in range(3):
        session.dispatch({"action": "undo"})
    assert captured(session) == []
    assert session.position == new_position()


def test_different_capture_after_undo_replaces_the_undone_one():
    session = Session()
    play_moves(session, *PAWN_TRADE)
    session.dispatch({"action": "undo"})
    play_moves(session, ("c8", "g4"))
    assert captured(session) == ["bP"]
    assert session.position[0]["d5"] == "wP"


def test_computer_capture_is_shown_and_undone_with_your_move():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    session.play("d7", "d5")  # Black's reply chosen for the test
    play_moves(session, ("e4", "d5"))
    # Recapturing with the queen is the computer's only move that keeps material level.
    view = session.dispatch({"action": "computer-move"})
    assert view["moves"][-1] == "d8xd5"
    assert view["captured"] == ["bP", "wP"]
    view = session.dispatch({"action": "undo"})
    assert view["captured"] == []
    assert view["turn"] == "w"
    assert session.position[0]["e4"] == "wP"
    assert session.position[0]["d5"] == "bP"


def test_load_restores_the_captured_pieces():
    first = Session()
    play_moves(first, *PAWN_TRADE)
    first.dispatch({"action": "save"})
    fresh = Session()
    assert fresh.dispatch({"action": "load"})["captured"] == ["bP", "wP"]


def test_undo_after_load_removes_a_capture_made_before_saving():
    first = Session()
    play_moves(first, *PAWN_TRADE)
    first.dispatch({"action": "save"})
    fresh = Session()
    fresh.dispatch({"action": "load"})
    fresh.dispatch({"action": "undo"})
    assert captured(fresh) == ["bP"]
    fresh.dispatch({"action": "undo"})
    assert captured(fresh) == []


def test_save_after_undo_does_not_bring_back_the_undone_capture():
    first = Session()
    play_moves(first, *PAWN_TRADE)
    first.dispatch({"action": "undo"})
    first.dispatch({"action": "save"})
    fresh = Session()
    assert fresh.dispatch({"action": "load"})["captured"] == ["bP"]


def test_new_game_and_load_replace_the_display():
    session = Session()
    play_moves(session, *PAWN_TRADE)
    session.dispatch({"action": "save"})
    assert session.dispatch({"action": "new"})["captured"] == []
    assert session.dispatch({"action": "load"})["captured"] == ["bP", "wP"]


def test_promotion_setup_shows_both_pawn_captures_and_undo_removes_one():
    session = Session()
    view = session.dispatch({"action": "promotion-setup"})
    assert view["captured"] == ["bP", "wP"]  # a6xb7 and h3xg2
    session.dispatch({"action": "undo"})
    assert captured(session) == ["bP"]
