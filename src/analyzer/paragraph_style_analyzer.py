from __future__ import annotations

from statistics import median

from src.models.document import Document
from src.models.enums.block_type import BlockType
from src.models.line import Line
from src.models.paragraph import Paragraph


class ParagraphStyleAnalyzer:
    """
    Calculates paragraph layout properties from PDF geometry.

    Current responsibilities:
    - Exact line spacing
    - Left indentation
    - Right indentation
    - First-line indentation
    """

    DEFAULT_LINE_SPACING = 12.0
    MINIMUM_LINE_SPACING = 6.0

    @staticmethod
    def analyze(document: Document) -> None:
        for page in document.pages:

            content_blocks = [
                block
                for block in page.blocks
                if (
                    block.block_type != BlockType.PAGE_NUMBER
                    and ParagraphStyleAnalyzer
                    ._block_has_text(block)
                )
            ]

            if not content_blocks:
                continue

            content_left = min(
                block.left
                for block in content_blocks
            )

            content_right = max(
                block.right
                for block in content_blocks
            )

            for block in content_blocks:
                for paragraph in block.paragraphs:
                    ParagraphStyleAnalyzer._analyze_paragraph(
                        paragraph=paragraph,
                        content_left=content_left,
                        content_right=content_right,
                    )

    @staticmethod
    def _analyze_paragraph(
        paragraph: Paragraph,
        content_left: float,
        content_right: float,
    ) -> None:
        """
        Populate horizontal and vertical paragraph properties.
        """

        visible_lines = [
            line
            for line in paragraph.lines
            if ParagraphStyleAnalyzer._line_has_text(line)
        ]

        if not visible_lines:
            return

        paragraph_left = min(
            ParagraphStyleAnalyzer._line_left(line)
            for line in visible_lines
        )

        paragraph_right = max(
            ParagraphStyleAnalyzer._line_right(line)
            for line in visible_lines
        )

        first_line_left = (
            ParagraphStyleAnalyzer._line_left(
                visible_lines[0]
            )
        )

        paragraph.style.left_indent = max(
            paragraph_left - content_left,
            0.0,
        )

        paragraph.style.right_indent = max(
            content_right - paragraph_right,
            0.0,
        )

        paragraph.style.first_line_indent = (
            first_line_left - paragraph_left
        )

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
    def _line_left(line: Line) -> float:
        """
        Return the left edge of visible content in a line.
        """

        visible_spans = [
            span
            for span in line.spans
            if span.text.strip()
        ]

        if not visible_spans:
            return 0.0

        return min(
            span.left
            for span in visible_spans
        )

    @staticmethod
    def _line_right(line: Line) -> float:
        """
        Return the right edge of visible content in a line.
        """

        visible_spans = [
            span
            for span in line.spans
            if span.text.strip()
        ]

        if not visible_spans:
            return 0.0

        return max(
            span.right
            for span in visible_spans
        )

    @staticmethod
    def _line_baseline(line: Line) -> float:
        """
        Return the median baseline of visible spans.
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
        Calculate one line's visible height.
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

        return max(
            bottom - top,
            ParagraphStyleAnalyzer.MINIMUM_LINE_SPACING,
        )

    @staticmethod
    def _line_has_text(line: Line) -> bool:
        """
        Return True when the line contains visible text.
        """

        return any(
            span.text.strip()
            for span in line.spans
        )

    @staticmethod
    def _block_has_text(block) -> bool:
        """
        Return True when the block contains visible text.
        """

        return any(
            span.text.strip()
            for line in block.lines
            for span in line.spans
        )