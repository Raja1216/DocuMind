from __future__ import annotations

from dataclasses import dataclass, field

from src.models.geometry.rectangle import Rectangle
from src.models.image import Image
from src.models.text_block import TextBlock
from src.models.table import Table
from src.models.vector_graphic import VectorGraphic

from src.models.vector_graphic_region import (
    VectorGraphicRegion,
)
from src.models.paragraph_region import (
    ParagraphRegion,
)
from src.models.page_profile import (
    PageProfile,
)
from src.models.conversion_policy import (
    ConversionPolicy,
)
from src.models.column_region import (
    ColumnRegion,
)

from src.models.layout_region import (
    LayoutRegion,
)
from src.models.reading_order import (
    ReadingDirection,
    ReadingOrderEntry,
)
from src.models.paragraph_alignment import (
    ParagraphAlignmentResult,
)
from src.models.list_item import (
    ListItemResult,
)
from src.models.list_sequence import (
    ListSequence,
)
from src.models.page_render_plan import (
    PageRenderPlan,
)
from src.models.editable_table import (
    EditableTable,
)
from src.models.editable_table_validation import (
    EditableTableValidationReport,
)

@dataclass(slots=True)
class Page:
    """
    Represents a single page in the document.
    """

    number: int

    bbox: Rectangle

    rotation: int

    blocks: list[TextBlock] = field(
        default_factory=list
    )

    images: list[Image] = field(
        default_factory=list
    )
    tables: list[Table] = field(
        default_factory=list
    )
    editable_tables: list[
        EditableTable
    ] = field(
        default_factory=list
    )

    editable_table_validation_reports: dict[
        str,
        EditableTableValidationReport
    ] = field(
        default_factory=dict
    )
    vector_graphics: list[VectorGraphic] = field(
        default_factory=list
    )
    vector_regions: list[VectorGraphicRegion] = field(
        default_factory=list
    )
    paragraph_regions: list[ParagraphRegion] = field(
        default_factory=list
    )
    list_item_results: list[
        ListItemResult
    ] = field(
        default_factory=list
    )
    list_sequences: list[
        ListSequence
    ] = field(
        default_factory=list
    )
    render_plan: PageRenderPlan = field(
        init=False
    )
    layout_regions: list[
        LayoutRegion
    ] = field(
        default_factory=list
    )
    
    column_regions: list[
        ColumnRegion
    ] = field(
        default_factory=list
    )
    reading_order_entries: list[
        ReadingOrderEntry
    ] = field(
        default_factory=list
    )
    paragraph_alignment_results: list[
        ParagraphAlignmentResult
    ] = field(
        default_factory=list
    )
    reading_direction: ReadingDirection = (
        ReadingDirection.LEFT_TO_RIGHT
    )
    profile: PageProfile = field(
        init=False
    )
    conversion_policy: ConversionPolicy | None = field(
        default=None,
        init=False,
    )
    def __post_init__(self) -> None:
        """
        Initialize the basic profile immediately when a Page is
        created.
    
        Content metrics and classification are filled later by
        PageProfileAnalyzer.
        """
        self.render_plan = PageRenderPlan(
            page_number=self.number
        )
        self.profile = PageProfile(
            page_number=self.number,
    
            page_width=max(
                float(self.bbox.width),
                0.0,
            ),
    
            page_height=max(
                float(self.bbox.height),
                0.0,
            ),
    
            rotation=(
                int(self.rotation)
                % 360
            ),
        )