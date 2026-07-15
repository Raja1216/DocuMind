from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Rectangle:
    """
    Represents a rectangular area in PDF coordinates.
    """

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top