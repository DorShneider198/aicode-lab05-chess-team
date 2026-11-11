import pytest

from game import new_position
from session import Session


def play_all(session, moves):
    for source, target in moves:
        session.play(source, target)


FOOLS_MATE = [("f2", "f3"), ("e7", "e5"), ("g2", "g4"), ("d8", "h4")]


def test_undo_at_the_start_does_nothing():
    session = Session()
    view = session.dispatch({"action": "undo"})
    assert session.position == new_position()
    assert view["moves"] == []
    assert view["can_undo"] is False


def test_undo_one_move_restores_board_turn_and_notation():
    session = Session()
    session.play("e2", "e4")
    assert session.view()["can_undo"] is True
    view = session.dispatch({"action": "undo"})
    assert session.position == new_position()
    assert view["turn"] == "w"
    assert view["moves"] == []
    assert view["can_undo"] is False


def test_undo_restores_a_captured_piece_and_side_to_move():
    session = Session()
    play_all(session, [("e2", "e4"), ("d7", "d5"), ("e4", "d5")])
    assert session.position[0]["d5"] == "wP"
    session.undo()
    assert session.position[0]["d5"] == "bP"
    assert session.position[0]["e4"] == "wP"
    assert session.position[1] == "w"
    assert session.notation == ["e2-e4", "d7-d5"]


def test_repeated_undo_returns_to_the_start_then_stops():
    session = Session()
    play_all(session, [("e2", "e4"), ("e7", "e5"), ("g1", "f3")])
    for _ in range(5):
        session.undo()
    assert session.position == new_position()
    assert session.notation == []


def test_undo_after_checkmate_resumes_the_game():
    session = Session()
    play_all(session, FOOLS_MATE)
    assert session.view()["status"] == "checkmate"
    session.undo()
    view = session.view()
    assert view["status"] is None
    assert view["winner"] is None
    assert view["turn"] == "b"
    assert "h4" in session.dispatch({"action": "legal", "source": "d8"})["targets"]


def test_illegal_move_is_not_recorded_for_undo():
    session = Session()
    with pytest.raises(ValueError):
        session.play("e2", "e5")
    assert session.history == []
    session.play("e2", "e4")
    session.undo()
    assert session.position == new_position()


def test_play_after_undo_continues_from_the_restored_position():
    session = Session()
    play_all(session, [("e2", "e4"), ("e7", "e5")])
    session.undo()
    session.play("d7", "d5")
    assert session.notation == ["e2-e4", "d7-d5"]
    assert session.position[0]["d5"] == "bP"
    assert "e5" not in session.position[0]


def test_undo_against_the_computer_takes_back_its_reply_and_your_move():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    session.dispatch({"action": "computer-move"})
    assert len(session.notation) == 2
    view = session.dispatch({"action": "undo"})
    assert session.position == new_position()
    assert view["turn"] == "w"
    assert view["moves"] == []
    assert not session.computer_to_move()


def test_undo_against_the_computer_keeps_earlier_moves():
    session = Session("computer")
    for source, target in [("e2", "e4"), ("d2", "d4")]:
        session.dispatch({"action": "move", "source": source, "target": target})
        session.dispatch({"action": "computer-move"})
    first_two = session.notation[:2]
    session.undo()
    assert session.notation == first_two
    assert session.position[1] == "w"
    assert session.position[0]["d2"] == "wP"


def test_undo_before_the_computer_replies_takes_back_only_your_move():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    assert session.computer_to_move()
    session.undo()
    assert session.position == new_position()
    assert not session.computer_to_move()


def test_undo_against_the_computer_after_you_checkmate_it():
    session = Session("computer")
    # Scholar's mate, with Black's moves played directly instead of chosen.
    play_all(session, [("e2", "e4"), ("e7", "e5"), ("f1", "c4"), ("b8", "c6"),
                       ("d1", "h5"), ("g8", "f6"), ("h5", "f7")])
    assert session.view()["status"] == "checkmate"
    session.undo()
    assert session.view()["status"] is None
    assert session.position[1] == "w"
    assert session.position[0]["h5"] == "wQ"
    assert session.notation[-1] == "g8-f6"


def test_new_game_clears_undo_history():
    session = Session()
    play_all(session, [("e2", "e4"), ("e7", "e5")])
    view = session.dispatch({"action": "new", "opponent": "computer"})
    assert view["can_undo"] is False
    session.undo()
    assert session.position == new_position()
    assert session.opponent == "computer"


def test_undo_keeps_the_opponent():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    session.undo()
    assert session.opponent == "computer"


def test_undo_after_promotion_setup():
    session = Session()
    session.dispatch({"action": "promotion-setup"})
    session.undo()
    assert session.position[0]["h3"] == "bP"
    assert session.position[0]["g2"] == "wP"  # h3xg2 captured it; undo brings it back
    assert len(session.notation) == 7


def test_undo_restores_state_that_other_features_add():
    # Features such as captured pieces keep extra per-move state on the session.
    class Tracking(Session):
        def __init__(self, opponent="human"):
            super().__init__(opponent)
            self.extra = []

        def after_move(self):
            self.extra = self.extra + [len(self.notation)]

    session = Tracking()
    play_all(session, [("e2", "e4"), ("e7", "e5")])
    assert session.extra == [1, 2]
    session.undo()
    assert session.extra == [1]
    session.undo()
    assert session.extra == []


def test_undo_history_is_not_shared_with_restored_state():
    session = Session()
    play_all(session, [("e2", "e4"), ("e7", "e5")])
    session.undo()
    session.position[0]["a3"] = "wN"
    session.undo()
    assert "a3" not in session.position[0]
