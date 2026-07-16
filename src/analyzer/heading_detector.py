from __future__ import annotations

from src.models.enums.block_type import BlockType
from src.models.page import Page


class HeadingDetector:
    """
    Detect headings using font size.
    """

    @staticmethod
    def detect(page: Page) -> None:

        largest_font = 0

        # Find largest font size
        for block in page.blocks:
            for line in block.lines:
                for span in line.spans:
                    largest_font = max(
                        largest_font,
                        span.font_size,
                    )

        # Mark heading blocks
        for block in page.blocks:

            for line in block.lines:
                for span in line.spans:

                    if span.font_size >= largest_font - 0.1:
                        block.block_type = BlockType.HEADING
                        break