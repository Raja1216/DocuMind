from dataclasses import dataclass


@dataclass(slots=True)
class DocumentStatistics:
    """
    Global statistics about a document.
    """

    largest_font_size: float = 0.0

    smallest_font_size: float = 0.0

    most_common_font_size: float = 0.0

    average_line_height: float = 0.0

    average_block_gap: float = 0.0