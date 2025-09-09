from decimal import Decimal
import fractions
from typing import Any

_COUNTER = 0


class Pebble:
    def __init__(self, position: str | float | Decimal | fractions.Fraction, name: str | None = None):
        self.position = fractions.Fraction(position)
        self.taken: Any = None
        global _COUNTER
        self.name = name if name is not None else f"P{_COUNTER}"
        _COUNTER += 1

    def get_position(self) -> fractions.Fraction:
        return self.position

    def __str__(self):
        return "Pebble(" + str(self.position) + ", " + str(self.taken) + ")"
