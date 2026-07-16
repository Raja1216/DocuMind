from __future__ import annotations

from statistics import median

from src.analyzer.block_classifier import BlockClassifier
from src.analyzer.line_reconstructor import LineReconstructor
from src.models.line import Line
from src.models.paragraph import Paragraph
from src.models.text_block import TextBlock


class ParagraphAnalyzer:
    """
    Reconstruct logical paragraphs from the lines inside a PDF text block.

    Version 2 rules:
    - Blank lines separate paragraphs.
    - Major font-size changes separate paragraphs.
    - Consecutive wrapped lines remain in the same paragraph.
    """

    FONT_SIZE_TOLERANCE = 0.5

    @staticmethod
    def analyze(block: TextBlock) -> None:
        block.block_type = BlockClassifier.classify(block)
        block.paragraphs.clear()

        current_lines: list[Line] = []
        current_font_size: float | None = None
        pending_spacing_before = 0.0

        for line in block.lines:
            line_text = ParagraphAnalyzer._line_text(line)

            # A whitespace-only PDF line represents visual separation.
            if not line_text.strip():
                if current_lines:
                    ParagraphAnalyzer._append_paragraph(
                        block=block,
                        lines=current_lines,
                        spacing_before=pending_spacing_before,
                    )

                    current_lines = []
                    current_font_size = None
                    pending_spacing_before = (
                        ParagraphAnalyzer._line_height(line)
                    )
                else:
                    pending_spacing_before += (
                        ParagraphAnalyzer._line_height(line)
                    )

                continue

            line_font_size = (
                ParagraphAnalyzer._dominant_font_size(line)
            )

            # A significant typography change usually indicates
            # a subtitle, heading, or a separate text section.
            if (
                current_lines
                and current_font_size is not None
                and abs(
                    line_font_size - current_font_size
                ) > ParagraphAnalyzer.FONT_SIZE_TOLERANCE
            ):
                ParagraphAnalyzer._append_paragraph(
                    block=block,
                    lines=current_lines,
                    spacing_before=pending_spacing_before,
                )

                current_lines = []
                pending_spacing_before = 0.0

            current_lines.append(line)

            if current_font_size is None:
                current_font_size = line_font_size

        if current_lines:
            ParagraphAnalyzer._append_paragraph(
                block=block,
                lines=current_lines,
                spacing_before=pending_spacing_before,
            )

    @staticmethod
    def _append_paragraph(
        block: TextBlock,
        lines: list[Line],
        spacing_before: float,
    ) -> None:
        """
        Create and store one reconstructed logical paragraph.
        """

        paragraph = Paragraph()

        paragraph.lines.extend(lines)

        paragraph.text = LineReconstructor.reconstruct(
            lines
        )

        paragraph.style.spacing_before = max(
            spacing_before,
            0.0,
        )

        paragraph.style.spacing_after = 0.0

        block.paragraphs.append(paragraph)

    @staticmethod
    def _line_text(line: Line) -> str:
        """
        Return all visible text contained in one PDF line.
        """

        return "".join(
            span.text
            for span in line.spans
        )

    @staticmethod
    def _dominant_font_size(line: Line) -> float:
        """
        Return the median font size used by a PDF line.
        """

        font_sizes = [
            span.font_size
            for span in line.spans
            if span.text.strip()
        ]

        if not font_sizes:
            return 0.0

        return float(
            median(font_sizes)
        )

    @staticmethod
    def _line_height(line: Line) -> float:
        """
        Calculate the visible line height using span geometry.
        """

        visible_spans = [
            span
            for span in line.spans
            if span.text
        ]

        if not visible_spans:
            return 0.0

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
            0.0,
        )