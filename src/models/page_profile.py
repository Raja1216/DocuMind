from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PageType(str, Enum):
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
    EDITABLE = "editable"
    FIXED = "fixed"
    HYBRID = "hybrid"
    OCR = "ocr"
    IMAGE_FALLBACK = "image_fallback"


@dataclass(slots=True)
class PageProfile:
    page_number: int

    page_type: PageType = PageType.UNKNOWN
    recommended_mode: ConversionMode = ConversionMode.HYBRID

    page_width: float = 0.0
    page_height: float = 0.0
    rotation: int = 0

    text_coverage: float = 0.0
    image_coverage: float = 0.0
    vector_coverage: float = 0.0
    table_coverage: float = 0.0

    text_block_count: int = 0
    paragraph_count: int = 0
    image_count: int = 0
    vector_count: int = 0
    table_count: int = 0
    chart_count: int = 0
    form_field_count: int = 0

    column_count: int = 1

    has_extractable_text: bool = False
    requires_ocr: bool = False

    has_header: bool = False
    has_footer: bool = False
    has_watermark: bool = False

    editable_confidence: float = 0.0
    fixed_confidence: float = 0.0
    ocr_confidence: float = 0.0

    warnings: list[str] = field(
        default_factory=list
    )