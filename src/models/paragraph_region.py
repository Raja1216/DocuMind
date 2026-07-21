from __future__ import annotations

from dataclasses import dataclass, field

from src.models.base_element import BaseElement
from src.models.line import Line
from src.models.paragraph_style import ParagraphStyle
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
)
from src.models.list_item import (
    ListMarkerKind,
    ListMarkerSource,
)

@dataclass(slots=True)
class ParagraphRegion(BaseElement):
    """
    Represents one logical, editable paragraph positioned on
    a PDF page.

    A region may contain lines originating from multiple
    PyMuPDF text blocks.
    """

    region_number: int

    lines: list[Line] = field(
        default_factory=list
    )

    text: str = ""

    source_block_numbers: list[int] = field(
        default_factory=list
    )

    style: ParagraphStyle = field(
        default_factory=ParagraphStyle
    )

    list_type: str | None = None
    list_marker: str | None = None
    list_level: int = 0

    list_marker_kind: ListMarkerKind = (
        ListMarkerKind.UNKNOWN
    )
    
    list_marker_source: ListMarkerSource = (
        ListMarkerSource.UNKNOWN
    )
    
    list_confidence: float = 0.0
    
    list_sequence_id: int | None = None
    list_item_index: int | None = None

    is_list_marker_only: bool = False
    list_content_region_number: int | None = None
    # Left position where the actual list-item content starts,
    # excluding a number such as "1.".
    content_left: float | None = None
    list_marker_left: float | None = None
    list_marker_right: float | None = None
    
    layout_region_id: int | None = None

    column_id: int | None = None
    
    reading_order: int | None = None
    
    detected_alignment: ParagraphAlignment = (
        ParagraphAlignment.UNKNOWN
    )
    
    alignment_confidence: float = 0.0
    
    alignment_reference_type: AlignmentReferenceType = (
        AlignmentReferenceType.UNKNOWN
    )
    
    alignment_reference_id: int | None = None

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