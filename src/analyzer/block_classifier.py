from __future__ import annotations

import re

from src.models.enums.block_type import BlockType
from src.models.text_block import TextBlock


class BlockClassifier:
    """
    Version 1

    Very simple rule-based classifier.
    """

    @staticmethod
    def classify(block: TextBlock) -> BlockType:

        text = " ".join(
            "".join(span.text for span in line.spans)
            for line in block.lines
        ).strip()

        # Empty block
        if not text:
            return BlockType.UNKNOWN

        # Page number
        if re.fullmatch(r"\d+", text):
            return BlockType.PAGE_NUMBER

        # Default
        return BlockType.PARAGRAPH