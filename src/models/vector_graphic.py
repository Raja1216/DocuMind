from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models.base_element import BaseElement


@dataclass(slots=True)
class VectorGraphic(BaseElement):
    """
    Represents one PDF vector-drawing group.

    A PyMuPDF drawing can contain one or more path items,
    such as lines, rectangles, curves, and quadrilaterals.
    """

    sequence_number: int

    drawing_type: str

    stroke_color: str | None = None
    fill_color: str | None = None

    stroke_width: float = 0.0

    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0

    even_odd_fill: bool = False
    close_path: bool = False

    line_cap: int | None = None
    line_join: int | None = None

    dash_pattern: str | None = None

    items: list[Any] = field(
        default_factory=list
    )
    
    category: str = "unknown"
    should_render: bool = True
    
    source_drawing: dict | None = None

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def area(self) -> float:
        return max(self.width, 0.0) * max(
            self.height,
            0.0,
        )