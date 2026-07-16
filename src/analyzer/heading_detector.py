from __future__ import annotations

from src.models.document import Document
from src.models.enums.block_type import BlockType


class HeadingDetector:
    """
    Detect headings using document statistics.
    """

    @staticmethod
    def detect(document: Document) -> None:

        body_font = document.statistics.most_common_font_size

        for page in document.pages:

            for block in page.blocks:

                largest = 0.0

                for line in block.lines:
                    for span in line.spans:
                        largest = max(largest, span.font_size)

                if largest >= body_font * 1.5:
                    block.block_type = BlockType.HEADING