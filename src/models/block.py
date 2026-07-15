from __future__ import annotations

from dataclasses import dataclass

from src.models.base_element import BaseElement


@dataclass(slots=True)
class Block(BaseElement):
    """
    Base class for page blocks.
    """

    block_number: int