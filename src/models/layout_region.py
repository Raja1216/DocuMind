from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.models.geometry.rectangle import (
    Rectangle,
)


class LayoutRegionType(str, Enum):
    """
    Semantic type of one page-layout container.

    A LayoutRegion represents a containing area rather than
    an individual paragraph or text span.
    """

    PAGE_BODY = "page_body"

    HEADER = "header"
    FOOTER = "footer"

    COLUMN = "column"
    SIDEBAR = "sidebar"

    TITLE_AREA = "title_area"
    TEXT_AREA = "text_area"

    TABLE_AREA = "table_area"
    FIGURE_AREA = "figure_area"
    CHART_AREA = "chart_area"
    FORM_AREA = "form_area"

    DECORATIVE_AREA = "decorative_area"

    UNKNOWN = "unknown"


@dataclass(slots=True)
class LayoutRegion:
    """
    Represents one semantic container on a PDF page.

    Examples:

        page body
        header
        footer
        column
        sidebar
        table area
        figure area

    Paragraphs and other elements can later be assigned to
    these containers.
    """

    region_id: int
    page_number: int

    region_type: LayoutRegionType

    bbox: Rectangle

    # Optional parent region. For example, a column can belong
    # to the page-body region.
    parent_region_id: int | None = None

    # Child regions contained by this region.
    child_region_ids: list[int] = field(
        default_factory=list
    )

    # ParagraphRegion.region_number values assigned to this
    # container.
    paragraph_region_numbers: list[int] = field(
        default_factory=list
    )

    # Original TextBlock numbers that contributed to this
    # region.
    source_block_numbers: list[int] = field(
        default_factory=list
    )

    # Filled later by the reading-order engine.
    reading_order: int | None = None

    confidence: float = 0.0

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

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

    @property
    def area(self) -> float:
        return (
            self.width
            * self.height
        )

    def add_child_region(
        self,
        region_id: int,
    ) -> None:
        if (
            region_id
            not in self.child_region_ids
        ):
            self.child_region_ids.append(
                region_id
            )

    def add_paragraph_region(
        self,
        region_number: int,
    ) -> None:
        if (
            region_number
            not in self.paragraph_region_numbers
        ):
            self.paragraph_region_numbers.append(
                region_number
            )

    def add_source_block(
        self,
        block_number: int,
    ) -> None:
        if (
            block_number
            not in self.source_block_numbers
        ):
            self.source_block_numbers.append(
                block_number
            )

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        self.confidence = max(
            0.0,
            min(
                float(confidence),
                1.0,
            ),
        )

    def add_reason(
        self,
        reason: str,
    ) -> None:
        normalized_reason = (
            reason.strip()
        )

        if (
            normalized_reason
            and normalized_reason
            not in self.reasons
        ):
            self.reasons.append(
                normalized_reason
            )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized_warning = (
            warning.strip()
        )

        if (
            normalized_warning
            and normalized_warning
            not in self.warnings
        ):
            self.warnings.append(
                normalized_warning
            )