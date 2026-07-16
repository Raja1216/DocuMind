from enum import Enum


class BlockType(str, Enum):
    """
    Logical type of a text block.
    """

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    SUBTITLE = "subtitle"
    PAGE_NUMBER = "page_number"
    UNKNOWN = "unknown"