"""The captured-pieces sidebar.

Captures are recorded when they happen, with the piece's type at capture. Comparing the
board with the starting pieces would also count a promoted pawn as captured.
"""


def add_capture(captured, piece):
    """Return the captured list with piece added, sorted for display."""
    return sorted(captured + [piece])
