from __future__ import annotations

from src.mapper.span_mapper import SpanMapper
from src.models.line import Line


class LineMapper:
    """
    Maps a PyMuPDF line dictionary into a DocuMind Line model.
    """

    @staticmethod
    def map(line_data: dict) -> Line:

        line = Line()

        for span in line_data["spans"]:
            line.spans.append(
                SpanMapper.map(span)
            )

        return line