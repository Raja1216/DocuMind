from dataclasses import dataclass


@dataclass(slots=True)
class ParagraphStyle:

    alignment: str = "left"

    left_indent: float = 0

    right_indent: float = 0

    first_line_indent: float = 0

    spacing_before: float = 0

    spacing_after: float = 0

    line_spacing: float = 1.0