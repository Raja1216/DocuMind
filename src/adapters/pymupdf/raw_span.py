from __future__ import annotations

from dataclasses import dataclass

from src.models.geometry.rectangle import Rectangle


@dataclass(slots=True, frozen=True)
class RawSpan:
    """
    Raw span extracted from PyMuPDF.

    This class represents PyMuPDF data,
    but isolates it from the rest of the application.
    """

    text: str

    font: str

    size: float

    color: int

    flags: int

    bbox: Rectangle

    origin_x: float

    origin_y: float