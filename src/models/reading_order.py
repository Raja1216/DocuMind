from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.models.geometry.rectangle import (
    Rectangle,
)


class ReadingDirection(str, Enum):
    """
    Dominant text direction of one PDF page.
    """

    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"


class ReadingOrderRole(str, Enum):
    """
    Semantic role of one paragraph in the page reading order.
    """

    HEADER = "header"

    BODY = "body"

    BODY_SPANNING = "body_spanning"

    COLUMN = "column"

    FOOTER = "footer"

    UNASSIGNED = "unassigned"


@dataclass(slots=True)
class ReadingOrderEntry:
    """
    One paragraph's resolved position in page reading order.
    """

    order: int

    page_number: int

    paragraph_region_number: int

    role: ReadingOrderRole

    bbox: Rectangle

    layout_region_id: int | None = None

    column_id: int | None = None

    @property
    def left(self) -> float:
        return float(
            self.bbox.left
        )

    @property
    def top(self) -> float:
        return float(
            self.bbox.top
        )

    @property
    def right(self) -> float:
        return float(
            self.bbox.right
        )

    @property
    def bottom(self) -> float:
        return float(
            self.bbox.bottom
        )

    @property
    def center_x(self) -> float:
        return (
            self.left + self.right
        ) / 2.0

    @property
    def center_y(self) -> float:
        return (
            self.top + self.bottom
        ) / 2.0