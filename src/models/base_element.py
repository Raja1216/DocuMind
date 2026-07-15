from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BaseElement:
    """
    Base class for every element in a document.
    """

    page_number: int

    left: float
    top: float
    right: float
    bottom: float