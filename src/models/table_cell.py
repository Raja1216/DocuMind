from __future__ import annotations

from dataclasses import dataclass

from src.models.base_element import BaseElement


@dataclass(slots=True)
class TableCell(BaseElement):
    """
    Represents one detected table cell.
    """

    row_index: int
    column_index: int

    text: str = ""

    row_span: int = 1
    column_span: int = 1
    
    fill_color: str | None = None

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top