from __future__ import annotations

from src.models.line import Line
from src.models.span import Span
from src.models.text_run import TextRun


class RunBuilder:
    """
    Converts PDF spans into logical Word runs.

    Consecutive spans are merged only when their visible
    formatting is identical.
    """

    @staticmethod
    def _is_bold(span: Span) -> bool:
        """
        PyMuPDF flag bit 4 indicates bold text.
        """

        return bool(span.flags & (1 << 4))

    @staticmethod
    def _is_italic(span: Span) -> bool:
        """
        PyMuPDF flag bit 1 indicates italic text.
        """

        return bool(span.flags & (1 << 1))

    @staticmethod
    def _create_run(span: Span) -> TextRun:
        """
        Create a TextRun from one Span.
        """

        return TextRun(
            text=span.text,
            font_name=span.font,
            font_size=span.font_size,
            color=span.color,
            bold=RunBuilder._is_bold(span),
            italic=RunBuilder._is_italic(span),
        )

    @staticmethod
    def _has_same_style(
        current: TextRun,
        span: Span,
    ) -> bool:
        """
        Check whether a span can be merged into the current run.
        """

        return (
            abs(current.font_size - span.font_size) <= 0.01
            and current.font_name == span.font
            and current.color == span.color
            and current.bold == RunBuilder._is_bold(span)
            and current.italic == RunBuilder._is_italic(span)
        )

    @staticmethod
    def build(line: Line) -> list[TextRun]:
        """
        Build logical Word runs from all spans in one PDF line.
        """

        runs: list[TextRun] = []
        current: TextRun | None = None

        for span in line.spans:

            if span.text == "":
                continue

            if current is None:
                current = RunBuilder._create_run(span)
                continue

            if RunBuilder._has_same_style(current, span):
                current.text += span.text
                continue

            runs.append(current)
            current = RunBuilder._create_run(span)

        if current is not None:
            runs.append(current)

        return runs