from __future__ import annotations

from dataclasses import dataclass

from src.models.base_element import BaseElement


@dataclass(slots=True)
class Image(BaseElement):
    """
    Represents one raster image displayed on a PDF page.
    """

    block_number: int

    image_bytes: bytes
    extension: str

    pixel_width: int
    pixel_height: int

    x_resolution: int
    y_resolution: int

    bits_per_component: int
    colorspace: int

    @property
    def displayed_width(self) -> float:
        """
        Width of the image on the PDF page in points.
        """

        return self.right - self.left

    @property
    def displayed_height(self) -> float:
        """
        Height of the image on the PDF page in points.
        """

        return self.bottom - self.top