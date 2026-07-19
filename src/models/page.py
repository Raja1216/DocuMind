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
    vector_graphics: list[VectorGraphic] = field(
        default_factory=list
    )
    vector_regions: list[VectorGraphicRegion] = field(
        default_factory=list
    )
    paragraph_regions: list[ParagraphRegion] = field(
        default_factory=list
    )
    profile: PageProfile = field(
        init=False
    )
    def __post_init__(self) -> None:
        """
        Initialize the basic profile immediately when a Page is
        created.
    
        Content metrics and classification are filled later by
        PageProfileAnalyzer.
        """
    
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