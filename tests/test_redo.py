"""Redo on its own: two players and against the computer."""

from game import new_position
from session import Session


def act(session, action, **fields):
    return session.dispatch({"action": action, **fields})


def play_moves(session, *moves):
    for source, target in moves:
        act(session, "move", source=source, target=target)


def test_redo_with_nothing_to_redo_does_nothing():
    session = Session()
    view = act(session, "redo")
    assert session.position == new_position()
    assert view["can_redo"] is False
    play_moves(session, ("e2", "e4"))
    before = session.view()
    assert act(session, "redo") == before


def test_redo_restores_the_undone_move():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    after = session.view()
    act(session, "undo")
    assert session.view()["can_redo"] is True
    view = act(session, "redo")
    assert view == after
    assert view["can_redo"] is False


def test_undo_several_then_redo_several_in_order():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    for _ in range(3):
        act(session, "undo")
    assert session.position == new_position()
    act(session, "redo")
    assert session.notation == ["e2-e4"]
    act(session, "redo")
    act(session, "redo")
    assert session.notation == ["e2-e4", "e7-e5", "g1-f3"]
    assert act(session, "redo")["can_redo"] is False


def test_redo_then_undo_again():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"))
    act(session, "undo")
    act(session, "redo")
    act(session, "undo")
    assert session.notation == ["e2-e4"]
    assert session.position[1] == "b"


def test_a_new_move_after_undo_discards_redo():
    session = Session()
    play_moves(session, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    act(session, "undo")
    act(session, "undo")
    view = act(session, "move", source="c7", target="c5")
    assert view["can_redo"] is False
    act(session, "redo")
    assert session.notation == ["e2-e4", "c7-c5"]
    assert "e5" not in session.position[0]


def test_new_game_clears_redo():
    session = Session()
    play_moves(session, ("e2", "e4"))
    act(session, "undo")
    view = act(session, "new", opponent="human")
    assert view["can_redo"] is False
    act(session, "redo")
    assert session.position == new_position()


def test_redo_against_the_computer_restores_your_move_and_its_reply():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    act(session, "computer-move")
    after = session.view()
    act(session, "undo")
    assert session.position == new_position()
    view = act(session, "redo")
    assert view == after  # the computer's original reply, not a new choice
    assert view["turn"] == "w"
    assert not session.computer_to_move()


def test_redo_against_the_computer_pair_by_pair():
    session = Session("computer")
    for source, target in [("e2", "e4"), ("d2", "d4")]:
        play_moves(session, (source, target))
        act(session, "computer-move")
    full = list(session.notation)
    act(session, "undo")
    act(session, "undo")
    act(session, "redo")
    assert session.notation == full[:2]
    act(session, "redo")
    assert session.notation == full


def test_redo_against_the_computer_when_it_had_not_replied():
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    act(session, "undo")  # only your move: the computer had not replied
    view = act(session, "redo")
    assert view["moves"] == ["e2-e4"]
    assert session.computer_to_move()


def test_redo_against_the_computer_restores_your_checkmate():
    session = Session("computer")
    # Scholar's mate, with Black's moves played directly instead of chosen.
    for source, target in [
        ("e2", "e4"),
        ("e7", "e5"),
        ("f1", "c4"),
        ("b8", "c6"),
        ("d1", "h5"),
        ("g8", "f6"),
        ("h5", "f7"),
    ]:
        session.play(source, target)
    assert session.view()["status"] == "checkmate"
    act(session, "undo")  # only your mating move
    act(session, "undo")  # g8-f6 and d1-h5
    act(session, "redo")
    assert session.notation[-1] == "g8-f6"
    assert session.position[1] == "w"
    view = act(session, "redo")
    assert view["status"] == "checkmate"
    assert view["can_redo"] is False
