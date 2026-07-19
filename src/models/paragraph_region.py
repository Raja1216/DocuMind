from __future__ import annotations

from dataclasses import dataclass, field

from src.models.base_element import BaseElement
from src.models.line import Line
from src.models.paragraph_style import ParagraphStyle


@dataclass(slots=True)
class ParagraphRegion(BaseElement):
    """
    Represents one logical, editable paragraph positioned on
    a PDF page.

    A region may contain lines originating from multiple
    PyMuPDF text blocks.
    """

    region_number: int

    lines: list[Line] = field(
        default_factory=list
    )

    text: str = ""

    source_block_numbers: list[int] = field(
        default_factory=list
    )

    style: ParagraphStyle = field(
        default_factory=ParagraphStyle
    )

    list_type: str | None = None
    list_marker: str | None = None
    list_level: int = 0

    # Left position where the actual list-item content starts,
    # excluding a number such as "1.".
    content_left: float | None = None
    list_marker_left: float | None = None
    list_marker_right: float | None = None

    @property
    def width(self) -> float:
        return max(
            self.right - self.left,
            0.0,
        )

    @property
    def height(self) -> float:
        return max(
            self.bottom - self.top,
            0.0,
        )