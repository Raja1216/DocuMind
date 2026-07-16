from __future__ import annotations

from dataclasses import dataclass, field

from src.models.block import Block
from src.models.line import Line
from src.models.enums.block_type import BlockType
from src.models.paragraph import Paragraph


@dataclass(slots=True)
class TextBlock(Block):
    """
    Represents a block containing text.
    """

    lines: list[Line] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)
    block_type: BlockType = BlockType.UNKNOWN