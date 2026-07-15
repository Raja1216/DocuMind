from __future__ import annotations

from dataclasses import dataclass, field

from src.models.block import Block
from src.models.line import Line


@dataclass(slots=True)
class TextBlock(Block):
    """
    Represents a block containing text.
    """

    lines: list[Line] = field(default_factory=list)