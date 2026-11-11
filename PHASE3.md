# Phase 3 guide: review, discussion, submission

Everything we need for the last 20 minutes, in one place. Details live in the files linked
from each section.

## 1. Steps, in order

1. `git switch main && git pull team main`. Work is committed on `main`; check
   `git status` shows nothing to commit (`.DS_Store` and `game.save.json` are fine).
2. Download the review skill `SKILL.md` into `.claude/skills/lab05-review/SKILL.md`.
   **Do not commit it.**
3. Start a **fresh** agent session in the repo and run `/lab05-review`.
   It writes `lab05-review.md` and changes nothing else.
4. While it runs: the discussion (section 3 below).
5. Read `lab05-review.md`. Pick **one** of its claims and check it in the code
   (section 5 below).
6. **Each** of us uploads `lab05-review.md` to "Lab 5 report" on Moodle **before the session
   ends**. The same file, uploaded twice.

## 2. Which file to open for what

| To show... | Open |
|---|---|
| The rules we were given (undo, save/load, redo requirements) | `README.md` ("Working together" section) |
| Who did what, merge by merge; the decisions; the bug | `DISCUSSION.md` |
| How to run the tests; every "features together" test; browser steps | `TESTING.md` |
| The check commands our agents must run | `CLAUDE.md` |
| The checking tools | `requirements-dev.txt` (ruff, mypy, pytest) |
| The code for undo, redo, save/load | `session.py` (`play`, `undo`, `redo`, `to_save`, `from_save`) |
| The captured-pieces fix | `captured.py`, and `Session.apply()` in `session.py` |
| The history of the work | `git log --oneline --graph` |

Tests: 130 in 11 files, all passing. "Together" files: `test_save_load_undo.py` (11),
`test_captured_together.py` (11), `test_promotion_together.py` (13),
`test_redo_together.py` (12).

## 3. The discussion questions, with our answers

**Which of the week's practices did we use?**

| Practice | Used? | Where to point |
|---|---|---|
| Tests for each feature | Yes | `test_save_load.py`, `test_undo.py`, `test_redo.py` (+ supplied `test_captured.py`, `test_promotion.py`) |
| Tests for features together | Yes, 47 tests | the four "together" files; table in `TESTING.md` |
| Tests run before and after every merge | Yes | `DISCUSSION.md` integration log |
| Manual checks in the browser | Yes | `TESTING.md`, "Manual checks" |
| Linting (ruff) | Yes, added late | found 3 issues; `DISCUSSION.md` |
| Formatting (ruff format) | Yes, added late | reformatted 9 files; later caught 2 unformatted test files |
| Type checking (mypy) | Yes, but weak | passes only because the code has no annotations |
| Check commands in an instruction file | Yes, added late | `CLAUDE.md` |

**What did the agent do without being asked?** (Dor's side; Maytav adds hers.)
- Wrote save/load tests with the feature, before being told (we had even asked whether
  tests belonged in that step: they do, the handout says "with its own tests").
- After the promotion merge passed all 95 tests, tried promotion with captured pieces by
  hand and found the promoted-pawn bug.
- Ran the new promotion tests against the old code to prove they catch the bug (6 failed).
- Ran mypy with `--check-untyped-defs` to show the plain `mypy .` pass says little.
- Made a failed load leave the current game unchanged, and wrote the save file atomically.

**What did we skip, and why?**
- Type annotations: mypy checks almost nothing without them; no time in the lab.
- Setting up ruff/mypy/`CLAUDE.md` **before** building: we added them after all merges.
- Automated tests for the browser code (`static/app.js`): checked by hand only.
- Extra features (castling, en passant, other draw rules): no time.
- Redo was built by one agent (Dor's), not by both of us together as the handout suggests.

**Where should we do better next time?**
- Set up the checks and `CLAUDE.md` first, so every agent runs them from the start.
- Write cross-feature tests for a supplied branch **before** merging it. The promotion bug
  passed every existing test because each branch was only tested alone.
- Decide shared data structures early: our two branches each made their own move list,
  and we had to combine them after merging.

## 4. Key points to say in one sentence each

- **The bug:** after merging promotion, a promoted pawn was listed as captured, because
  captured pieces were computed by comparing the board with the starting pieces. Fixed by
  recording each capture when it happens. All tests had passed; only a combined check found
  it. (`DISCUSSION.md`, "Bug found when merging promotion")
- **Undo against the computer (Maytav):** takes back your move and the computer's reply,
  so it is your turn again.
- **Redo against the computer (Dor):** the exact reverse: your move and the computer's
  **original** reply come back. (`DISCUSSION.md`, "Redo decisions")
- **One history:** undo, redo and save/load all use `Session.history`; a pointer
  (`played`) says how many moves are on the board.
- **Merge conflicts:** in two merges (save/load + undo, then promotion), always both sides
  adding lines in the same place; we kept both each time. Captured-pieces merged cleanly.

## 5. Checking one claim in the review

Choose a claim from `lab05-review.md` that names a file or behavior, then verify it:
- About tests: `python -m pytest -v -k <word>` and read the named test.
- About checks: run the four commands from `CLAUDE.md`.
- About behavior: open `session.py` at the function it names, or try it in the browser.
Say whether the claim held up; that is part of the discussion.

## 6. Redo summary (latest step)

- **What redo does:** brings back the last undone move, including its capture and the
  promotion piece chosen. Disabled when there is nothing to redo; a new move or new game
  clears it; it survives save/load (undone moves are saved under `"redo"`).
- **Against the computer:** your move and the computer's original reply, so it is your
  turn again: the exact reverse of undo. Replaying the original reply means redo restores
  exactly what undo removed instead of letting the computer pick something new.
- **Tests that prove it works with the rest:** `test_redo_together.py`: capture display,
  promotion piece, the computer's capture, save/load (also with promotion and the computer),
  a new move after load, new game after load, a bad redo list in the save file.
- **What broke:** no game bug. Six older tests assumed `history` only holds moves on the
  board; their helper was updated. `ruff format --check` flagged two new test files.
