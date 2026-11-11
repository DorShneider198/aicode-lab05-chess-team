# Discussion notes

Notes for the Phase 3 discussion: how the features were integrated, what broke, and
which practices we used.

## Integration log

| Step | Who | What happened |
|---|---|---|
| `feature/save-load` | Dor | Save writes the opponent and the move list; load replays the moves in a fresh game. |
| `feature/undo` | Maytav | Snapshot of the game before each move; undo against the computer takes back its reply and your move. |
| Merge save/load + undo | Dor | Two conflicts (`session.py`, `index.html`): both sides added lines in the same place; kept both. |
| One move list | Dor | Each branch kept its own list (`moves` for save, `history` for undo). Combined into one `history`: each entry holds the move and the state before it. |
| Merge captured-pieces | Maytav | Merged cleanly; added `tests/test_captured_together.py` and `TESTING.md`. |
| Merge promotion | Dor | One conflict in `Session.play()`: undo's snapshot and promotion's new `promotion` argument. Kept both, and the history also stores the chosen piece so a saved promotion can be replayed. |
| Promotion bug | Dor | Found and fixed; see below. |
| Checking tools | Dor | Added ruff, mypy and `CLAUDE.md` with the four check commands. |
| `feature/redo` | Dor | Redo on the same `history` list as undo (no second history); merged into `main`. See "Redo decisions". |

## Redo decisions

- **Same mechanism as undo.** `history` keeps every move; `played` counts how many are on
  the board. Undo moves `played` back and restores that entry's "before" snapshot instead
  of deleting the entry. Redo replays the next stored move (with its promotion piece) and
  moves `played` forward, so captures and the captured list come back through the normal
  move code. A new move after undo cuts `history` at `played`, which discards redo.
- **Against the computer: the exact reverse of undo.** Undo takes back your move and the
  computer's reply, so redo puts both back and it is your turn again. It replays the
  computer's original reply rather than letting it choose again, so redo always restores
  exactly what undo removed. If undo took back only your move (the computer had not
  replied, or your move ended the game), redo restores only that move; if the computer is
  then to move, the browser asks it for a reply as usual.
- **Save/load.** The save file keeps `moves` (on the board) and, only when there is
  something to redo, `redo` (the undone moves). Load replays both, then steps back over
  the `redo` moves, so they can be redone after loading. Old save files still load.
- **Nothing to redo, new game:** redo does nothing; new game clears it. The Redo button is
  disabled when there is nothing to redo.

**What broke.** Nothing in the game. Six tests in `test_save_load_undo.py` failed because
their helper assumed `history` holds only the moves on the board; with redo, undone moves
stay in `history`. The helper now checks `played` instead. When the four checks were run,
`ruff format --check` flagged two new test files, fixed with `ruff format`.

**Tests added.** `tests/test_redo.py` (10 tests, redo alone) and
`tests/test_redo_together.py` (12 tests, redo with captures, promotion, the computer,
save/load and new game). 130 tests in total.

## Bug found when merging promotion: a promoted pawn was listed as captured

**Symptom.** Play the README's promotion moves, then b7xa8=Q. The captured list showed
`bP, bR, wP, wP`: the rook was correct, but there was an extra white pawn.
A promotion with no capture at all also listed the pawn as captured.

**Cause.** The captured-pieces branch did not record captures. It compared the board with
the starting pieces and listed whatever was missing. After a promotion the pawn is missing
from the board, so it counted as captured; the new queen was ignored because the count only
looks for missing pieces. This breaks the README rule "Promotion alone is not a capture".
The same approach would also show a captured promoted queen as a pawn, not as a queen.

**Why every test still passed.** The captured-pieces tests were written before promotion
existed, and the promotion tests never look at the captured list. Each feature was
correct on its own branch; the bug only exists when both are merged. All 95 tests passed
after the merge, and the bug was found only by trying the combination directly.

**Fix.** `Session.play()` now records the piece on the target square at the moment it is
captured (`captured.add_capture`), instead of comparing with the starting board. Undo
restores the list from its snapshot, and load rebuilds it by replaying moves, so neither
needed changes.

**Tests added.** `tests/test_promotion_together.py` (13 tests): promotion alone is not a
capture, a capturing promotion lists only the captured piece, a captured promoted piece
shows as its type at capture, undo, save/load, undo after load, a bad promotion in a save
file, and new game. Run against the old code, 6 of them fail; with the fix all pass
(108 tests in total).

## Practices we used (for the discussion questions)

- **Tests for each feature:** yes — `test_save_load.py`, `test_undo.py`, plus the supplied
  `test_captured.py` and `test_promotion.py`.
- **Tests for features together:** yes — `test_save_load_undo.py`,
  `test_captured_together.py`, `test_promotion_together.py`. The promotion bug shows why:
  separate tests all passed while the combined game was wrong.
- **Ran the tests after every merge:** yes, before and after each merge.
- **Manual checks in the browser:** yes; steps are in `TESTING.md`.
- **Checked that new tests catch the bug:** the new promotion tests were run against the
  old code to confirm they fail there.
- **Linting, formatting, type checking:** added late, after all four features were merged.
  `ruff check` found 3 issues (unsorted imports, and two `ValueError`s that should be
  `TypeError`); `ruff format` reformatted 9 files. `mypy .` passed, but only because the code
  has no type annotations, so mypy skips most function bodies; with `--check-untyped-defs`
  it reports 4 findings, none of them a real bug.
- **Check commands in an instruction file:** `CLAUDE.md` lists the four checks and says to
  run them before reporting any task as done. Also added late.

Do better next time: add the linter, type checker and `CLAUDE.md` before building the
features, so every agent runs the checks from the start without being asked.
Write the cross-feature tests for a supplied branch before merging it, not after.
