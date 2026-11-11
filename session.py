"""Application actions and information shown beside the board."""

import json
import os
from pathlib import Path

from computer import choose_move
from game import (
    legal_moves,
    move,
    new_position,
    status,
    winner,
)


# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"), ("h7", "h5"),
    ("a4", "a5"), ("h5", "h4"),
    ("a5", "a6"), ("h4", "h3"),
    ("a6", "b7"), ("h3", "g2"),
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
        self.opponent = opponent
        # Every move played, as [source, target]; save/load replays these.
        self.moves = []

    def play(self, source, target):
        label = move(self.position, source, target)
        self.notation.append(label)
        self.moves.append([source, target])
        self.after_move()

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

    def to_save(self):
        """The game as plain data: the opponent and every move played."""
        return {"version": SAVE_VERSION, "opponent": self.opponent,
                "moves": [list(m) for m in self.moves]}

    @classmethod
    def from_save(cls, data):
        """Rebuild a game by replaying saved moves; raise ValueError if invalid."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("Not a saved game")
        moves = data.get("moves")
        if not isinstance(moves, list):
            raise ValueError("Saved game has no move list")
        session = cls(data.get("opponent"))
        for entry in moves:
            if not isinstance(entry, list) or len(entry) < 2:
                raise ValueError("Saved game has a malformed move")
            session.play(*entry)
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
        return (self.opponent == "computer" and self.position[1] == "b"
                and status(self.position) not in ("checkmate", "stalemate"))

    def sidebar(self):
        return {}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "legal":
            return {"targets": legal_moves(self.position, action.get("source"))}
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
