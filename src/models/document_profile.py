from __future__ import annotations

from dataclasses import dataclass, field

from src.models.page_profile import (
    ConversionMode,
    PageType,
)


@dataclass(slots=True)
class DocumentProfile:
    """
    Stores document-level analysis results.

    This profile summarizes all page profiles but does not
    force every page to use the same conversion mode.
    """

    page_count: int = 0

    # ---------------------------------------------------------
    # Page-content categories
    # ---------------------------------------------------------

    digital_page_count: int = 0
    scanned_page_count: int = 0
    mixed_page_count: int = 0

    simple_text_page_count: int = 0
    multi_column_page_count: int = 0
    designed_page_count: int = 0

    table_page_count: int = 0
    chart_page_count: int = 0
    form_page_count: int = 0
    image_dominant_page_count: int = 0

    # ---------------------------------------------------------
    # Overall classification
    # ---------------------------------------------------------

    dominant_page_type: PageType = (
        PageType.UNKNOWN
    )

    recommended_mode: ConversionMode = (
        ConversionMode.HYBRID
    )

    # ---------------------------------------------------------
    # Document capabilities and features
    # ---------------------------------------------------------

    contains_tables: bool = False
    contains_charts: bool = False
    contains_forms: bool = False

    contains_scanned_pages: bool = False
    contains_digital_pages: bool = False

    contains_headers: bool = False
    contains_footers: bool = False
    contains_watermarks: bool = False

    contains_multiple_page_sizes: bool = False
    contains_multiple_orientations: bool = False

    requires_ocr: bool = False
    requires_hybrid_conversion: bool = False

    # ---------------------------------------------------------
    # Confidence scores
    # ---------------------------------------------------------

    editable_confidence: float = 0.0
    fixed_confidence: float = 0.0
    hybrid_confidence: float = 0.0
    ocr_confidence: float = 0.0

    # Number of pages assigned to each conversion mode.
    mode_counts: dict[str, int] = field(
        default_factory=dict
    )

    # Number of pages assigned to each page type.
    page_type_counts: dict[str, int] = field(
        default_factory=dict
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
        normalized_warning = warning.strip()

        if (
            normalized_warning
            and normalized_warning
            not in self.warnings
        ):
            self.warnings.append(
                normalized_warning
            )