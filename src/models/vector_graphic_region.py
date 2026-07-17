from __future__ import annotations

from dataclasses import dataclass, field

from src.models.base_element import BaseElement
from src.models.vector_graphic import VectorGraphic


@dataclass(slots=True)
class VectorGraphicRegion(BaseElement):
    """
    Represents one logical region containing multiple
    nearby vector graphics.

    During Step 61 this only stores grouped vectors.

    Later it will also contain a rendered transparent PNG.
    """

    region_number: int

    graphics: list[VectorGraphic] = field(
        default_factory=list
    )

    image_path: str | None = None

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top