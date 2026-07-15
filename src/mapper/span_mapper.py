from __future__ import annotations

from src.models.span import Span
from src.models.color.rgb_color import RGBColor


class SpanMapper:
    """
    Maps a PyMuPDF span dictionary into a DocuMind Span model.
    """

    @staticmethod
    def map(span_data: dict) -> Span:
        bbox = span_data["bbox"]
        origin = span_data["origin"]

        return Span(
            text=span_data["text"],
            font=span_data["font"],
            font_size=span_data["size"],
            color=RGBColor.from_pymupdf(span_data["color"]),
            flags=span_data["flags"],
            left=bbox[0],
            top=bbox[1],
            right=bbox[2],
            bottom=bbox[3],
            origin_x=origin[0],
            origin_y=origin[1],
        )