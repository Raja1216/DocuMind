from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RGBColor:
    """
    Represents an RGB color.
    """

    red: int
    green: int
    blue: int

    @staticmethod
    def from_pymupdf(color: int) -> "RGBColor":
        """
        Convert PyMuPDF integer color to RGBColor.
        """

        red = (color >> 16) & 255
        green = (color >> 8) & 255
        blue = color & 255

        return RGBColor(red, green, blue)

    def to_hex(self) -> str:
        """
        Convert to HTML HEX format.
        """

        return f"#{self.red:02X}{self.green:02X}{self.blue:02X}"