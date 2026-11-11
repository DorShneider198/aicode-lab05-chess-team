"""Save/load: a saved game is restored in a fresh session, through the actions."""

import json

import pytest

from session import Session


@pytest.fixture
def save_file(tmp_path, monkeypatch):
    path = tmp_path / "game.save.json"
    monkeypatch.setattr(Session, "save_path", path)
    return path


def play_moves(session, *moves):
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def test_load_restores_game_in_fresh_session(save_file):
    first = Session()
    play_moves(first, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    saved_view = first.dispatch({"action": "save"})

    fresh = Session()
    assert fresh.dispatch({"action": "load"}) == saved_view
    assert fresh.position[1] == "b"
    assert fresh.notation == ["e2-e4", "d7-d5", "e4xd5"]
    assert fresh.position[0]["d5"] == "wP"
    assert len(fresh.position[0]) == 31


def test_load_keeps_the_move_list_for_undo(save_file):
    first = Session()
    play_moves(first, ("g1", "f3"), ("b8", "c6"))
    first.dispatch({"action": "save"})

    fresh = Session()
    fresh.dispatch({"action": "load"})
    assert fresh.moves == [["g1", "f3"], ["b8", "c6"]]


def test_save_file_holds_opponent_and_moves(save_file):
    session = Session("computer")
    play_moves(session, ("e2", "e4"))
    session.dispatch({"action": "save"})
    assert json.loads(save_file.read_text()) == {
        "version": 1, "opponent": "computer", "moves": [["e2", "e4"]]}


def test_load_restores_computer_opponent_and_its_turn(save_file):
    first = Session("computer")
    play_moves(first, ("e2", "e4"))
    first.dispatch({"action": "save"})

    fresh = Session()
    view = fresh.dispatch({"action": "load"})
    assert view["opponent"] == "computer"
    assert fresh.computer_to_move()
    fresh.dispatch({"action": "computer-move"})
    assert fresh.position[1] == "w"
    assert len(fresh.notation) == 2


def test_play_continues_after_load(save_file):
    first = Session()
    play_moves(first, ("e2", "e4"))
    first.dispatch({"action": "save"})
    fresh = Session()
    fresh.dispatch({"action": "load"})
    play_moves(fresh, ("e7", "e5"))
    assert fresh.notation == ["e2-e4", "e7-e5"]
    assert fresh.moves[-1] == ["e7", "e5"]


def test_save_at_start_and_load_gives_new_game(save_file):
    Session().dispatch({"action": "save"})
    fresh = Session()
    play_moves(fresh, ("e2", "e4"))
    view = fresh.dispatch({"action": "load"})
    assert view == Session().view()
    assert fresh.moves == []


def test_new_game_after_load_clears_it(save_file):
    first = Session("computer")
    play_moves(first, ("e2", "e4"))
    first.dispatch({"action": "save"})
    session = Session()
    session.dispatch({"action": "load"})
    view = session.dispatch({"action": "new", "opponent": "human"})
    assert view == Session().view()
    assert session.moves == []


def test_later_save_overwrites_earlier(save_file):
    session = Session()
    play_moves(session, ("e2", "e4"))
    session.dispatch({"action": "save"})
    play_moves(session, ("e7", "e5"))
    session.dispatch({"action": "save"})
    fresh = Session()
    fresh.dispatch({"action": "load"})
    assert fresh.notation == ["e2-e4", "e7-e5"]


def test_load_without_save_fails_and_keeps_game(save_file):
    session = Session()
    play_moves(session, ("e2", "e4"))
    before = session.view()
    with pytest.raises(ValueError, match="No saved game"):
        session.dispatch({"action": "load"})
    assert session.view() == before


@pytest.mark.parametrize("content", [
    "not json",
    json.dumps([1, 2]),
    json.dumps({"version": 99, "opponent": "human", "moves": []}),
    json.dumps({"version": 1, "opponent": "robot", "moves": []}),
    json.dumps({"version": 1, "opponent": "human", "moves": "e2e4"}),
    json.dumps({"version": 1, "opponent": "human", "moves": [["e2"]]}),
    json.dumps({"version": 1, "opponent": "human", "moves": [["e2", "e5"]]}),
    json.dumps({"version": 1, "opponent": "human",
                "moves": [["e2", "e4"], ["e4", "e5"]]}),
])
def test_bad_save_file_is_rejected_and_game_unchanged(save_file, content):
    save_file.write_text(content)
    session = Session()
    play_moves(session, ("d2", "d4"))
    before = session.view()
    with pytest.raises(ValueError):
        session.dispatch({"action": "load"})
    assert session.view() == before
    assert session.moves == [["d2", "d4"]]


def test_load_through_http_server_in_fresh_instance(save_file):
    """Save in one server, load in a second one, as after a restart."""
    import threading
    import urllib.request

    from server import make_server

    def post(port, action):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/action", data=json.dumps(action).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    views = []
    for actions in ([{"action": "new", "opponent": "computer"},
                     {"action": "move", "source": "e2", "target": "e4"},
                     {"action": "save"}],
                    [{"action": "load"}]):
        server = make_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for action in actions:
                view = post(server.server_port, action)
            views.append(view)
        finally:
            server.shutdown()
            server.server_close()
    assert views[1] == views[0]
    assert views[1]["opponent"] == "computer"
    assert views[1]["turn"] == "b"
