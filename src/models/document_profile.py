from __future__ import annotations

from dataclasses import dataclass, field

from src.models.page_profile import (
    ConversionMode,
    PageType,
)


@dataclass(slots=True)
class DocumentProfile:
    page_count: int = 0

    digital_page_count: int = 0
    scanned_page_count: int = 0
    mixed_page_count: int = 0

    dominant_page_type: PageType = PageType.UNKNOWN
    recommended_mode: ConversionMode = ConversionMode.HYBRID

    contains_tables: bool = False
    contains_charts: bool = False
    contains_forms: bool = False
    contains_scanned_pages: bool = False
    contains_multiple_page_sizes: bool = False

    warnings: list[str] = field(
        default_factory=list
    )