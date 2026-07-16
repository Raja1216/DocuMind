from __future__ import annotations

from dataclasses import dataclass

from src.models.color.rgb_color import RGBColor


@dataclass(slots=True)
class TextRun:
    """
    Represents a logical Word run.

    Consecutive PDF spans with identical visible formatting
    are merged into one TextRun.
    """

    text: str

    font_name: str
    font_size: float
    color: RGBColor

    bold: bool = False
    italic: bool = False