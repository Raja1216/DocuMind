from __future__ import annotations

from src.models.text_block import TextBlock


class LayoutAnalyzer:
    """
    Analyze the spatial relationship between text blocks.
    """

    @staticmethod
    def vertical_gap(
        current: TextBlock,
        next_block: TextBlock,
    ) -> float:
        """
        Returns the vertical distance between two blocks.
        """

        return next_block.top - current.bottom