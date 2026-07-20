from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.models.geometry.rectangle import (
    Rectangle,
)


class ParagraphAlignment(str, Enum):
    """
    Alignment detected from PDF paragraph and line geometry.

    UNKNOWN is used until the alignment analyzer has enough
    evidence to make a reliable decision.
    """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"
    UNKNOWN = "unknown"


class AlignmentReferenceType(str, Enum):
    """
    Container relative to which alignment was calculated.

    Alignment must normally be measured against the nearest
    semantic container rather than against the complete page.
    """

    COLUMN = "column"
    PAGE_BODY = "page_body"

    HEADER = "header"
    FOOTER = "footer"

    LAYOUT_REGION = "layout_region"

    PAGE = "page"

    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParagraphAlignmentResult:
    """
    Stores the alignment analysis result for one paragraph.

    This model contains measurements and decisions only.
    It does not modify or render a Word paragraph.
    """

    page_number: int

    paragraph_region_number: int

    alignment: ParagraphAlignment = (
        ParagraphAlignment.UNKNOWN
    )

    confidence: float = 0.0

    # ---------------------------------------------------------
    # Alignment reference container
    # ---------------------------------------------------------

    reference_type: AlignmentReferenceType = (
        AlignmentReferenceType.UNKNOWN
    )

    # ColumnRegion.column_id or LayoutRegion.region_id.
    reference_id: int | None = None

    # Geometry of the paragraph itself.
    paragraph_bbox: Rectangle | None = None

    # Geometry of the column, page body, header, footer, or
    # fallback page used for alignment comparison.
    reference_bbox: Rectangle | None = None

    # ---------------------------------------------------------
    # Paragraph-to-container measurements
    # ---------------------------------------------------------

    left_gap: float = 0.0
    right_gap: float = 0.0

    # Signed difference:
    #
    # paragraph center - reference center
    #
    # Negative means left of the reference center.
    # Positive means right of the reference center.
    center_offset: float = 0.0

    # Paragraph width divided by reference width.
    width_ratio: float = 0.0

    # ---------------------------------------------------------
    # Line measurements
    # ---------------------------------------------------------

    line_count: int = 0

    # Differences among visible line-left edges.
    left_edge_variance: float = 0.0

    # Differences among visible line-right edges.
    right_edge_variance: float = 0.0

    # Width of the final line divided by the reference width.
    last_line_width_ratio: float = 0.0

    # Width of the final line divided by the previous normal
    # line width. Useful for justified-text detection.
    last_line_relative_width: float = 0.0

    has_hanging_indent: bool = False

    # ---------------------------------------------------------
    # Decision details
    # ---------------------------------------------------------

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def paragraph_width(self) -> float:
        if self.paragraph_bbox is None:
            return 0.0

        return max(
            float(
                self.paragraph_bbox.right
            )
            - float(
                self.paragraph_bbox.left
            ),
            0.0,
        )

    @property
    def paragraph_height(self) -> float:
        if self.paragraph_bbox is None:
            return 0.0

        return max(
            float(
                self.paragraph_bbox.bottom
            )
            - float(
                self.paragraph_bbox.top
            ),
            0.0,
        )

    @property
    def reference_width(self) -> float:
        if self.reference_bbox is None:
            return 0.0

        return max(
            float(
                self.reference_bbox.right
            )
            - float(
                self.reference_bbox.left
            ),
            0.0,
        )

    @property
    def absolute_center_offset(
        self,
    ) -> float:
        return abs(
            self.center_offset
        )

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Set confidence while keeping the value between
        0.0 and 1.0.
        """

        self.confidence = max(
            0.0,
            min(
                float(confidence),
                1.0,
            ),
        )

    def set_width_ratio(
        self,
        width_ratio: float,
    ) -> None:
        """
        Store a valid paragraph/reference width ratio.
        """

        self.width_ratio = max(
            0.0,
            min(
                float(width_ratio),
                1.0,
            ),
        )

    def set_last_line_width_ratio(
        self,
        width_ratio: float,
    ) -> None:
        self.last_line_width_ratio = max(
            0.0,
            min(
                float(width_ratio),
                1.0,
            ),
        )

    def set_last_line_relative_width(
        self,
        width_ratio: float,
    ) -> None:
        self.last_line_relative_width = max(
            0.0,
            float(width_ratio),
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