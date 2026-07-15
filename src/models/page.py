from dataclasses import dataclass


@dataclass(slots=True)
class Page:
    """
    Represents a single PDF page.
    """

    number: int

    width: float
    height: float

    left: float
    top: float
    right: float
    bottom: float

    rotation: int