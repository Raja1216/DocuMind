from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Span:
    """
    Represents the smallest piece of formatted text.
    """

    text: str

    font: str

    font_size: float

    color: int

    flags: int

    left: float
    top: float
    right: float
    bottom: float

    origin_x: float
    origin_y: float