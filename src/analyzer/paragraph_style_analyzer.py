from __future__ import annotations

from statistics import median

from src.models.document import Document
from src.models.line import Line
from src.models.paragraph import Paragraph


class ParagraphStyleAnalyzer:
    """
    Calculates paragraph layout properties from PDF geometry.

    Current responsibility:
    - Calculate exact line spacing in points.
    """

    DEFAULT_LINE_SPACING = 12.0
    MINIMUM_LINE_SPACING = 6.0

    @staticmethod
    def analyze(document: Document) -> None:
        for page in document.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    paragraph.style.line_spacing = (
                        ParagraphStyleAnalyzer
                        ._calculate_line_spacing(paragraph)
                    )

    @staticmethod
    def _calculate_line_spacing(
        paragraph: Paragraph,
    ) -> float:
        """
        Calculate the typical baseline distance between
        consecutive PDF lines.

        The result is returned in points.
        """

        lines = [
            line
            for line in paragraph.lines
            if ParagraphStyleAnalyzer._line_has_text(line)
        ]

        if not lines:
            return (
                ParagraphStyleAnalyzer.DEFAULT_LINE_SPACING
            )

        if len(lines) == 1:
            return (
                ParagraphStyleAnalyzer
                ._single_line_height(lines[0])
            )

        baseline_positions = [
            ParagraphStyleAnalyzer._line_baseline(line)
            for line in lines
        ]

        baseline_gaps = [
            current - previous
            for previous, current in zip(
                baseline_positions,
                baseline_positions[1:],
            )
            if current > previous
        ]

        if not baseline_gaps:
            return (
                ParagraphStyleAnalyzer
                ._single_line_height(lines[0])
            )

        calculated_spacing = float(
            median(baseline_gaps)
        )

        return max(
            calculated_spacing,
            ParagraphStyleAnalyzer.MINIMUM_LINE_SPACING,
        )

    @staticmethod
    def _line_baseline(line: Line) -> float:
        """
        Return the median baseline position of visible spans.
        """

        baselines = [
            span.origin_y
            for span in line.spans
            if span.text.strip()
        ]

        if not baselines:
            return 0.0

        return float(
            median(baselines)
        )

    @staticmethod
    def _single_line_height(line: Line) -> float:
        """
        Calculate line height using visible span boundaries.
        """

        visible_spans = [
            span
            for span in line.spans
            if span.text.strip()
        ]

        if not visible_spans:
            return (
                ParagraphStyleAnalyzer.DEFAULT_LINE_SPACING
            )

        top = min(
            span.top
            for span in visible_spans
        )

        bottom = max(
            span.bottom
            for span in visible_spans
        )

        height = bottom - top

        return max(
            height,
            ParagraphStyleAnalyzer.MINIMUM_LINE_SPACING,
        )

    @staticmethod
    def _line_has_text(line: Line) -> bool:
        """
        Return True if a line contains visible text.
        """

        return any(
            span.text.strip()
            for span in line.spans
        )