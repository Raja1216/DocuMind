from __future__ import annotations

from dataclasses import dataclass, field

from src.models.block import Block


@dataclass(slots=True)
class TextBlock(Block):
    """
    Represents a block containing text.
    """

    lines: list = field(default_factory=list)