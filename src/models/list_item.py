from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ListMarkerKind(str, Enum):
    """
    Normalized marker style detected from PDF content.
    """

    BULLET = "bullet"

    DECIMAL = "decimal"
    MULTILEVEL_DECIMAL = "multilevel_decimal"

    LOWER_ALPHA = "lower_alpha"
    UPPER_ALPHA = "upper_alpha"

    LOWER_ROMAN = "lower_roman"
    UPPER_ROMAN = "upper_roman"

    UNKNOWN = "unknown"


class ListMarkerSource(str, Enum):
    """
    Origin of a detected list marker.
    """

    TEXT = "text"
    VECTOR = "vector"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ListItemResult:
    """
    Normalized list information for one paragraph.

    Sequence grouping and nesting are added in Step 62.9G.2.
    """

    page_number: int
    paragraph_region_number: int

    list_type: str

    marker: str

    marker_kind: ListMarkerKind = (
        ListMarkerKind.UNKNOWN
    )

    marker_source: ListMarkerSource = (
        ListMarkerSource.UNKNOWN
    )

    marker_left: float | None = None
    marker_right: float | None = None
    content_left: float | None = None

    level: int = 0

    confidence: float = 0.0

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
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