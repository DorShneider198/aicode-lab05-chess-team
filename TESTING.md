# Testing

How to rerun the automated checks and repeat the manual checks in the browser.

## Running the automated tests

```sh
source .venv/bin/activate
python -m pytest                                   # everything
python -m pytest tests/test_captured_together.py   # one file
python -m pytest -k undo                           # tests whose name contains "undo"
python -m pytest tests/test_undo.py::test_undo_at_the_start_does_nothing   # one test
python -m pytest -v                                # list every test by name
```

Tests that save a game write to a temporary file, never to `game.save.json`.

## Test files

| File | Covers |
|---|---|
| `tests/test_game.py` | Movement, check, checkmate, stalemate, notation, new game |
| `tests/test_computer.py` | The computer opponent and new games against it |
| `tests/test_undo.py` | Undo alone: one move, captures, the start, checkmate, against the computer |
| `tests/test_save_load.py` | Save/load alone: fresh session, opponent, bad or missing save file, HTTP server |
| `tests/test_save_load_undo.py` | Save/load and undo together: undo after loading, save after undo |
| `tests/test_captured.py` | Captured pieces alone (supplied with the branch) |
| `tests/test_captured_together.py` | Captured pieces with undo, save/load and the computer |

## Features working together

Each row is an interaction and the test that establishes it.

| Interaction | Test |
|---|---|
| Undo removes a capture from the display | `test_captured_together.py::test_undo_removes_a_capture_from_the_display` |
| Undo of a quiet move keeps earlier captures | `test_captured_together.py::test_undo_of_a_quiet_move_keeps_earlier_captures` |
| Repeated undo empties the display | `test_captured_together.py::test_repeated_undo_empties_the_display` |
| A different capture after undo replaces the undone one | `test_captured_together.py::test_different_capture_after_undo_replaces_the_undone_one` |
| Undo against the computer removes its capture together with your move | `test_captured_together.py::test_computer_capture_is_shown_and_undone_with_your_move` |
| Load restores the captured pieces | `test_captured_together.py::test_load_restores_the_captured_pieces` |
| Undo after load removes a capture made before saving | `test_captured_together.py::test_undo_after_load_removes_a_capture_made_before_saving` |
| Save after undo does not bring back the undone capture | `test_captured_together.py::test_save_after_undo_does_not_bring_back_the_undone_capture` |
| New game clears the display; load restores it | `test_captured_together.py::test_new_game_and_load_replace_the_display` |
| Moves made before saving can be undone after loading | `test_save_load_undo.py::test_moves_made_before_saving_can_be_undone_after_loading` |
| A loaded computer game undoes your move and its reply | `test_save_load_undo.py::test_loaded_computer_game_undoes_your_move_and_its_reply` |
| Save after undo stores only the current line | `test_save_load_undo.py::test_save_after_undo_stores_the_current_line_only` |

## Manual checks in the browser

Start the server with `python3 server.py` and open http://127.0.0.1:8000. Moves are written
as source-target: `e2-e4` means click the piece on e2, then the square e4.

**Captured pieces**
1. New game: two players. Play e2-e4, d7-d5, e4-d5 (capture).
   Expected: "Captured pieces" shows a black pawn.
2. Play d8-d5 (the queen recaptures).
   Expected: a black pawn and a white pawn.
3. New game. Expected: the list shows "None".

**Undo**
1. Repeat steps 1-2 above, then press Undo.
   Expected: the white pawn is back on d5, only the black pawn is listed, Black to move.
2. Press Undo three more times.
   Expected: the starting position, "None" captured, and Undo is disabled.
3. Press Undo again. Expected: nothing changes.

**Undo against the computer**
1. New game: play the computer. Play e2-e4 and wait for its reply. Play one more move and
   wait. If it captured something, the piece is listed.
2. Press Undo.
   Expected: both the computer's reply and your last move are taken back, it is your
   move, and any piece it captured is back on the board and gone from the list.

**Save and load**
1. New game: two players. Play e2-e4, d7-d5, e4-d5. Press Save game.
2. New game. Expected: empty board history, "None" captured.
3. Press Load saved game.
   Expected: the three moves are back, the black pawn is listed, Black to move.
4. Press Undo. Expected: the capture is taken back and the list shows "None".
5. Against the computer: save, start a two-player game, load.
   Expected: the opponent is the computer again ("Your move" / "The computer is thinking").

**Promotion setup (for the next merge)**
Two-player game: a2-a4, h7-h5, a4-a5, h5-h4, a5-a6, h4-h3, a6-b7 (capture),
h3-g2 (capture). Expected: a black pawn and a white pawn are listed. White's b7 pawn can
now move to a8.
