from __future__ import annotations

from dataclasses import dataclass, field

from src.models.geometry.rectangle import (
    Rectangle,
)


@dataclass(slots=True)
class ColumnRegion:
    """
    Represents one detected content column.

    A column is measured relative to its containing layout
    region, not necessarily relative to the complete page.
    """

    column_id: int
    page_number: int

    # Zero-based horizontal position:
    #
    # 0 = first/leftmost column
    # 1 = second column
    # 2 = third column
    column_index: int

    bbox: Rectangle

    parent_region_id: int | None = None

    paragraph_region_numbers: list[int] = field(
        default_factory=list
    )

    source_block_numbers: list[int] = field(
        default_factory=list
    )

    # Reading order among columns. Usually this is left to
    # right, but right-to-left documents may differ.
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