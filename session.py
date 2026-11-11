"""Application actions and information shown beside the board."""

import copy

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


class Session:
    def __init__(self, opponent="human"):
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation = []
        self.opponent = opponent
        # Snapshots of the game state before each move, oldest first.
        self.history = []

    # Attributes that belong to the whole game rather than to one point in it.
    # Everything else (position, notation, and state added by other features)
    # is saved before each move and restored by undo.
    GAME_WIDE = ("opponent", "history")

    def snapshot(self):
        return {name: copy.deepcopy(value) for name, value in vars(self).items()
                if name not in self.GAME_WIDE}

    def restore(self, snapshot):
        for name, value in copy.deepcopy(snapshot).items():
            setattr(self, name, value)

    def play(self, source, target):
        before = self.snapshot()
        label = move(self.position, source, target)
        self.history.append(before)
        self.notation.append(label)
        self.after_move()

    def undo(self):
        """Take back the last move; against the computer, return the turn to White.

        Two players: one half-move. Against the computer: the computer's reply
        and the player's move, so the player moves next. If the computer has not
        replied (White's move ended the game, or it is still thinking), only the
        player's move is taken back. At the start of a game, nothing happens.
        """
        if not self.history:
            return
        steps = 1
        if self.opponent == "computer" and self.position[1] == "w" and len(self.history) >= 2:
            steps = 2
        for _ in range(steps):
            self.restore(self.history.pop())

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "can_undo": bool(self.history),
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

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
        elif command == "undo":
            self.undo()
        elif command == "legal":
            return {"targets": legal_moves(self.position, action.get("source"))}
        elif command == "new":
            self.__init__(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.__init__()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
