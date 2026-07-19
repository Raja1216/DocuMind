from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PageType(str, Enum):
    """
    High-level structural classification of one PDF page.

    These values describe the page itself, not the complete
    document. A single PDF may contain multiple page types.
    """

    SIMPLE_TEXT = "simple_text"
    MULTI_COLUMN = "multi_column"
    DESIGNED_COVER = "designed_cover"

    TABLE_DOMINANT = "table_dominant"
    CHART_DOMINANT = "chart_dominant"
    FORM = "form"

    IMAGE_DOMINANT = "image_dominant"
    SCANNED = "scanned"
    MAGAZINE = "magazine"

    MIXED = "mixed"
    UNKNOWN = "unknown"


class ConversionMode(str, Enum):
    """
    Recommended conversion strategy for one page.
    """

    EDITABLE = "editable"
    FIXED = "fixed"
    HYBRID = "hybrid"

    OCR = "ocr"
    IMAGE_FALLBACK = "image_fallback"


@dataclass(slots=True)
class PageProfile:
    """
    Stores analysis results for one PDF page.

    The PageProfile does not perform analysis itself. The
    PageProfileAnalyzer introduced in Step 62.5G.2 will fill
    these fields.
    """

    page_number: int

    page_type: PageType = (
        PageType.UNKNOWN
    )

    recommended_mode: ConversionMode = (
        ConversionMode.HYBRID
    )

    # ---------------------------------------------------------
    # Page geometry
    # ---------------------------------------------------------

    page_width: float = 0.0
    page_height: float = 0.0
    rotation: int = 0

    # ---------------------------------------------------------
    # Content coverage
    #
    # Values should remain between 0.0 and 1.0.
    # ---------------------------------------------------------

    text_coverage: float = 0.0
    image_coverage: float = 0.0
    vector_coverage: float = 0.0
    table_coverage: float = 0.0
    chart_coverage: float = 0.0

    # ---------------------------------------------------------
    # Detected element counts
    # ---------------------------------------------------------

    text_block_count: int = 0
    paragraph_count: int = 0
    image_count: int = 0
    vector_count: int = 0
    vector_region_count: int = 0

    table_count: int = 0
    chart_count: int = 0
    form_field_count: int = 0

    # ---------------------------------------------------------
    # Layout structure
    # ---------------------------------------------------------

    column_count: int = 1

    has_extractable_text: bool = False
    requires_ocr: bool = False

    has_header: bool = False
    has_footer: bool = False
    has_watermark: bool = False

    # ---------------------------------------------------------
    # Confidence scores
    #
    # Values should remain between 0.0 and 1.0.
    # ---------------------------------------------------------

    editable_confidence: float = 0.0
    fixed_confidence: float = 0.0
    hybrid_confidence: float = 0.0
    ocr_confidence: float = 0.0

    # Human-readable explanations produced by analyzers.
    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def page_area(self) -> float:
        """
        Return the page area in PDF square points.
        """

        width = max(
            self.page_width,
            0.0,
        )

        height = max(
            self.page_height,
            0.0,
        )

        return width * height

    @property
    def aspect_ratio(self) -> float:
        """
        Return width divided by height.
        """

        if self.page_height <= 0:
            return 0.0

        return (
            self.page_width
            / self.page_height
        )

    @property
    def is_landscape(self) -> bool:
        """
        Return True when the page is wider than it is tall.
        """

        return (
            self.page_width
            > self.page_height
        )

    @property
    def is_portrait(self) -> bool:
        """
        Return True when the page is taller than or equal to
        its width.
        """

        return not self.is_landscape

    def add_reason(
        self,
        reason: str,
    ) -> None:
        """
        Add one classification explanation without creating
        duplicates.
        """

        normalized_reason = reason.strip()

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
        """
        Add one warning without creating duplicates.
        """

        normalized_warning = warning.strip()

        if (
            normalized_warning
            and normalized_warning
            not in self.warnings
        ):
            self.warnings.append(
                normalized_warning
            )