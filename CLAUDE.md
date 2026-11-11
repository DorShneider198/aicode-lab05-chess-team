# Chess workshop: instructions for coding agents

A local chess game in Python (see `README.md`). Game rules are in `game.py`, actions and
undo/save/load in `session.py`, the browser UI in `static/`. Tests are in `tests/`;
`TESTING.md` lists them and the manual browser checks.

## Setup

```sh
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Checks

Before reporting any task as done, run all four from the repository root, with `.venv`
active, and make sure every one passes:

```sh
ruff check .
ruff format --check .
mypy .
python -m pytest
```

- If `ruff format --check .` fails, run `ruff format .` and check again.
- Fix findings in the code; do not silence rules with `noqa` comments or `type: ignore`.
- Also run the checks after every merge, before changing anything to repair it.

## Working rules

- Each feature goes on its own branch from `main`, with its own tests.
- When a change affects more than one feature (undo, save/load, captured pieces,
  promotion, redo), add a test for the features together, not only for each one alone.
- Tests that save a game must use a temporary file (see the `save_file` fixtures), never
  `game.save.json`.
