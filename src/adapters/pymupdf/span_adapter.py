from __future__ import annotations

from src.adapters.pymupdf.raw_span import RawSpan
from src.models.geometry.rectangle import Rectangle


class SpanAdapter:
    """
    Converts PyMuPDF dictionaries
    into RawSpan objects.
    """

    @staticmethod
    def adapt(span_data: dict) -> RawSpan:

        bbox = span_data["bbox"]

        return RawSpan(
            text=span_data["text"],
            font=span_data["font"],
            size=span_data["size"],
            color=span_data["color"],
            flags=span_data["flags"],
            bbox=Rectangle(
                left=bbox[0],
                top=bbox[1],
                right=bbox[2],
                bottom=bbox[3],
            ),
            origin_x=span_data["origin"][0],
            origin_y=span_data["origin"][1],
        )