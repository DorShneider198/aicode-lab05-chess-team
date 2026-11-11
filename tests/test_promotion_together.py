"""Promotion with captured pieces, undo, save/load and new game."""

import json

import pytest

from session import PROMOTION_SETUP, Session


@pytest.fixture(autouse=True)
def save_file(tmp_path, monkeypatch):
    path = tmp_path / "game.save.json"
    monkeypatch.setattr(Session, "save_path", path)
    return path


def act(session, action, **fields):
    return session.dispatch({"action": action, **fields})


def promoted_game():
    """The README's promotion shortcut, then b7xa8=Q (captures the rook on a8)."""
    session = Session()
    act(session, "promotion-setup")
    act(session, "move", source="b7", target="a8", promotion="Q")
    return session


def from_position(board, turn="w"):
    session = Session()
    session.position = [board, turn]
    return session


# The bug found while merging: a promoted pawn appeared in the captured list.
def test_promotion_alone_is_not_a_capture():
    session = from_position({"a7": "wP", "e1": "wK", "h8": "bK"})
    view = act(session, "move", source="a7", target="a8", promotion="Q")
    assert session.position[0]["a8"] == "wQ"
    assert view["captured"] == []


def test_capturing_promotion_lists_only_the_captured_piece():
    session = Session()
    before = act(session, "promotion-setup")["captured"]
    assert before == ["bP", "wP"]
    view = act(session, "move", source="b7", target="a8", promotion="Q")
    assert view["moves"][-1].startswith("b7xa8=Q")
    assert view["captured"] == ["bP", "bR", "wP"]  # the rook, not the promoted pawn


def test_captured_promoted_piece_shows_its_type_at_capture():
    session = from_position({"a7": "wP", "e1": "wK", "g8": "bK", "b8": "bR"})
    act(session, "move", source="a7", target="a8", promotion="Q")
    view = act(session, "move", source="b8", target="a8")
    assert view["captured"] == ["wQ"]


def test_black_promotion_is_not_a_capture():
    session = promoted_game()
    view = act(session, "move", source="g2", target="h1", promotion="N")
    assert session.position[0]["h1"] == "bN"
    assert view["captured"] == ["bP", "bR", "wP", "wR"]  # g2xh1 took the rook


def test_undo_promotion_restores_the_pawn_and_the_captured_list():
    session = promoted_game()
    view = act(session, "undo")
    assert session.position[0]["b7"] == "wP"
    assert session.position[0]["a8"] == "bR"
    assert view["captured"] == ["bP", "wP"]
    assert view["turn"] == "w"
    assert act(session, "legal", source="b7")["promotions"] == ["a8", "c8"]


def test_play_a_different_promotion_after_undo():
    session = promoted_game()
    act(session, "undo")
    view = act(session, "move", source="b7", target="a8", promotion="N")
    assert session.position[0]["a8"] == "wN"
    assert view["moves"][-1].startswith("b7xa8=N")
    assert view["captured"] == ["bP", "bR", "wP"]


def test_save_and_load_keep_the_promoted_piece(save_file):
    act(promoted_game(), "save")
    assert json.loads(save_file.read_text())["moves"][-1] == ["b7", "a8", "Q"]
    fresh = Session()
    view = act(fresh, "load")
    assert fresh.position[0]["a8"] == "wQ"
    assert view["moves"][-1].startswith("b7xa8=Q")
    assert view["captured"] == ["bP", "bR", "wP"]


def test_undo_after_load_takes_back_the_promotion():
    act(promoted_game(), "save")
    fresh = Session()
    act(fresh, "load")
    view = act(fresh, "undo")
    assert fresh.position[0]["b7"] == "wP"
    assert view["captured"] == ["bP", "wP"]


def test_save_after_undoing_the_promotion_keeps_the_pawn():
    session = promoted_game()
    act(session, "undo")
    act(session, "save")
    fresh = Session()
    view = act(fresh, "load")
    assert fresh.position[0]["b7"] == "wP"
    assert fresh.position[0]["a8"] == "bR"
    assert view["captured"] == ["bP", "wP"]


SETUP = [list(m) for m in PROMOTION_SETUP]


@pytest.mark.parametrize("moves", [
    SETUP + [["b7", "a8"]],        # promotion without a chosen piece
    SETUP + [["b7", "a8", "K"]],   # promotion to a king
    [["e2", "e4", "Q"]],           # a piece choice on an ordinary move
])
def test_bad_promotion_in_save_file_is_rejected(save_file, moves):
    save_file.write_text(json.dumps({"version": 1, "opponent": "human", "moves": moves}))
    session = Session()
    before = session.view()
    with pytest.raises(ValueError):
        act(session, "load")
    assert session.view() == before


def test_new_game_after_promotion_clears_everything():
    session = promoted_game()
    view = act(session, "new", opponent="human")
    assert view == Session().view()
