from __future__ import annotations

from dataclasses import dataclass, field

from src.models.text_block import TextBlock
from src.models.geometry.rectangle import Rectangle


@dataclass(slots=True)
class Page:
    """
    Represents a single page in the document.
    """

    number: int

    bbox: Rectangle

    rotation: int

    blocks: list[TextBlock] = field(default_factory=list)