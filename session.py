"""Application actions and information shown beside the board."""

import copy
import json
import os
from pathlib import Path

from captured import add_capture
from computer import choose_move
from game import (
    legal_moves,
    move,
    new_position,
    promotes,
    status,
    winner,
)

# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"),
    ("h7", "h5"),
    ("a4", "a5"),
    ("h5", "h4"),
    ("a5", "a6"),
    ("h4", "h3"),
    ("a6", "b7"),
    ("h3", "g2"),
]


SAVE_VERSION = 1


class Session:
    # Where the save/load actions keep the game. Tests point an instance elsewhere.
    save_path = Path(__file__).parent / "game.save.json"

    def __init__(self, opponent="human"):
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation = []
        self.captured = []
        self.opponent = opponent
        # The single list of moves, oldest first. Each entry holds the move
        # ([source, target], plus the promotion piece if any) and the game state
        # just before it. The first `played` entries are on the board; the rest
        # were undone and can be redone. Undo restores "before"; redo and
        # save/load replay "move".
        self.history = []
        self.played = 0

    # Attributes that belong to the whole game rather than to one point in it.
    # Everything else (position, notation, and state added by other features)
    # is saved before each move and restored by undo.
    GAME_WIDE = ("opponent", "history", "played")

    def snapshot(self):
        return {
            name: copy.deepcopy(value)
            for name, value in vars(self).items()
            if name not in self.GAME_WIDE
        }

    def restore(self, snapshot):
        for name, value in copy.deepcopy(snapshot).items():
            setattr(self, name, value)

    def play(self, source, target, promotion=None):
        """Play a new move. After undo, this discards the moves that could be redone."""
        entry = self.apply(source, target, promotion)
        del self.history[self.played :]
        self.history.append(entry)
        self.played += 1

    def apply(self, source, target, promotion=None):
        """Make a move on the board and return its history entry."""
        before = self.snapshot()
        taken = self.position[0].get(
            target
        )  # the piece as it is now, e.g. a promoted queen
        label = move(self.position, source, target, promotion)
        if taken:
            self.captured = add_capture(self.captured, taken)
        # A promotion move also records the chosen piece, so load can replay it.
        played = [source, target] + ([promotion] if promotion else [])
        self.notation.append(label)
        self.after_move()
        return {"move": played, "before": before}

    def undo(self):
        """Take back the last move; against the computer, return the turn to White.

        Two players: one half-move. Against the computer: the computer's reply
        and the player's move, so the player moves next. If the computer has not
        replied (White's move ended the game, or it is still thinking), only the
        player's move is taken back. At the start of a game, nothing happens.
        """
        if not self.played:
            return
        steps = 1
        if self.opponent == "computer" and self.position[1] == "w" and self.played >= 2:
            steps = 2
        for _ in range(steps):
            self.played -= 1
            self.restore(self.history[self.played]["before"])

    def redo(self):
        """Replay the last undone move: the exact reverse of undo.

        Two players: one half-move. Against the computer: your move and the
        computer's original reply, so it is your turn again. If undo took back
        only your move (the computer had not replied), only that move comes back.
        With nothing to redo, nothing happens.
        """
        undone = len(self.history) - self.played
        if not undone:
            return
        steps = 1
        if self.opponent == "computer" and self.position[1] == "w" and undone >= 2:
            steps = 2
        for _ in range(steps):
            self.history[self.played] = self.apply(*self.history[self.played]["move"])
            self.played += 1

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "can_undo": self.played > 0,
            "can_redo": self.played < len(self.history),
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

    def past_moves(self):
        """The moves on the board, oldest first, as [source, target(, promotion)]."""
        return [list(entry["move"]) for entry in self.history[: self.played]]

    def redo_moves(self):
        """The undone moves that redo would replay, in playing order."""
        return [list(entry["move"]) for entry in self.history[self.played :]]

    def to_save(self):
        """The game as plain data: the opponent, every move played, and any redo."""
        data = {
            "version": SAVE_VERSION,
            "opponent": self.opponent,
            "moves": self.past_moves(),
        }
        if self.redo_moves():
            data["redo"] = self.redo_moves()
        return data

    @classmethod
    def from_save(cls, data):
        """Rebuild a game by replaying saved moves; raise ValueError or TypeError if invalid."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("Not a saved game")
        moves = data.get("moves")
        if not isinstance(moves, list):
            raise TypeError("Saved game has no move list")
        redo = data.get("redo", [])
        if not isinstance(redo, list):
            raise TypeError("Saved game has a malformed redo list")
        session = cls(data.get("opponent"))
        for entry in moves + redo:
            if not isinstance(entry, list) or len(entry) < 2:
                raise ValueError("Saved game has a malformed move")
            session.play(*entry)
        # Step back over the redo moves so they can be redone after loading.
        if redo:
            session.played = len(moves)
            session.restore(session.history[session.played]["before"])
        return session

    def save(self):
        temporary = self.save_path.with_name(self.save_path.name + ".tmp")
        temporary.write_text(json.dumps(self.to_save()))
        os.replace(temporary, self.save_path)

    def load(self):
        """Replace this game with the saved one; leave it unchanged on failure."""
        try:
            data = json.loads(self.save_path.read_text())
        except FileNotFoundError:
            raise ValueError("No saved game") from None
        except json.JSONDecodeError:
            raise ValueError("Saved game is unreadable") from None
        loaded = Session.from_save(data)
        self.__dict__.update(loaded.__dict__)

    def computer_to_move(self):
        return (
            self.opponent == "computer"
            and self.position[1] == "b"
            and status(self.position) not in ("checkmate", "stalemate")
        )

    def sidebar(self):
        return {"captured": self.captured}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(
                action.get("source"), action.get("target"), action.get("promotion")
            )
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "undo":
            self.undo()
        elif command == "redo":
            self.redo()
        elif command == "legal":
            source = action.get("source")
            targets = legal_moves(self.position, source)
            return {
                "targets": targets,
                "promotions": [
                    t for t in targets if promotes(self.position, source, t)
                ],
            }
        elif command == "new":
            self.__init__(action.get("opponent", "human"))
        elif command == "save":
            self.save()
        elif command == "load":
            self.load()
        elif command == "promotion-setup":
            self.__init__()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
