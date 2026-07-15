from __future__ import annotations

from src.mapper.line_mapper import LineMapper
from src.models.text_block import TextBlock


class BlockMapper:
    """
    Maps a PyMuPDF text block dictionary
    into a DocuMind TextBlock.
    """

    @staticmethod
    def map(block_data: dict, page_number: int) -> TextBlock:

        bbox = block_data["bbox"]

        block = TextBlock(
            page_number=page_number,

            left=bbox[0],
            top=bbox[1],
            right=bbox[2],
            bottom=bbox[3],

            block_number=block_data["number"],
        )

        for line in block_data["lines"]:
            block.lines.append(
                LineMapper.map(line)
            )

        return block