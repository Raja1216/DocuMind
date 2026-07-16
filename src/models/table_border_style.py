from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TableBorderStyle:
    """
    Represents the dominant border appearance of a PDF table.
    """

    color: str = "#B7B7B7"
    thickness: float = 0.5