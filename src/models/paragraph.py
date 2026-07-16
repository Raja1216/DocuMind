from __future__ import annotations

from dataclasses import dataclass, field

from src.models.line import Line
from src.models.paragraph_style import ParagraphStyle


@dataclass(slots=True)
class Paragraph:
    """
    Logical paragraph reconstructed from one or more PDF lines.
    """

    lines: list[Line] = field(default_factory=list)
    text: str = ""
    style: ParagraphStyle = field(
        default_factory=ParagraphStyle
    )