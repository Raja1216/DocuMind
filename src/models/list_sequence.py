from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.models.list_item import (
    ListMarkerKind,
    ListMarkerSource,
)


class ListContainerType(str, Enum):
    """
    Container relative to which list indentation is measured.
    """

    COLUMN = "column"
    PAGE_BODY = "page_body"
    LAYOUT_REGION = "layout_region"
    PAGE = "page"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ListSequenceItem:
    """
    One ordered item inside a detected list sequence.
    """

    page_number: int
    paragraph_region_number: int

    item_index: int
    level: int

    marker: str
    marker_kind: ListMarkerKind
    marker_source: ListMarkerSource

    indent: float

    numeric_value: int | None = None
    multilevel_value: tuple[int, ...] | None = None


@dataclass(slots=True)
class ListSequence:
    """
    A consecutive logical list on one PDF page.

    Cross-page continuation will be handled by the exporter in
    Step 62.9G.3.
    """

    sequence_id: int
    page_number: int

    list_type: str

    container_type: ListContainerType
    container_id: int | None

    container_left: float
    container_right: float

    start_at: int = 1
    maximum_level: int = 0

    confidence: float = 0.0

    items: list[ListSequenceItem] = field(
        default_factory=list
    )

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def add_reason(
        self,
        reason: str,
    ) -> None:
        value = reason.strip()

        if value and value not in self.reasons:
            self.reasons.append(
                value
            )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        value = warning.strip()

        if value and value not in self.warnings:
            self.warnings.append(
                value
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