from __future__ import annotations

from dataclasses import dataclass
from src.models.color.rgb_color import RGBColor


@dataclass(slots=True)
class Span:
    """
    Represents the smallest piece of formatted text.
    """

    text: str

    font: str

    font_size: float

    color: RGBColor

    flags: int

    left: float
    top: float
    right: float
    bottom: float

    origin_x: float
    origin_y: float