from __future__ import annotations

from dataclasses import dataclass, field

from src.models.span import Span


@dataclass(slots=True)
class Line:
    """
    Represents one line of text.
    """

    spans: list[Span] = field(default_factory=list)