from __future__ import annotations

from dataclasses import dataclass, field

from src.models.line import Line


@dataclass(slots=True)
class Paragraph:
    """
    Logical paragraph reconstructed from one or more PDF lines.
    """

    lines: list[Line] = field(default_factory=list)
    text: str = ""