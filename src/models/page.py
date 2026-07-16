from __future__ import annotations

from dataclasses import dataclass, field

from src.models.geometry.rectangle import Rectangle
from src.models.image import Image
from src.models.text_block import TextBlock
from src.models.table import Table
from src.models.vector_graphic import VectorGraphic


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