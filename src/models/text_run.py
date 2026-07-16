from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextRun:
    """
    Logical Word run.

    A run groups consecutive spans that share
    the same formatting.
    """

    text: str

    font_size: float

    font_name: str

    color: int

    flags: int