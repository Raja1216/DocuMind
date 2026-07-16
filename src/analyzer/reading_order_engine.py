from __future__ import annotations

from src.models.text_block import TextBlock


class ReadingOrderEngine:
    """
    Determines the reading order of text blocks.
    Version 1:
    - Single column
    - Top-to-bottom
    - Left-to-right
    """

    @staticmethod
    def sort_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
        """
        Sort blocks into human reading order.
        """

        return sorted(
            blocks,
            key=lambda block: (
                block.top,
                block.left,
            ),
        )