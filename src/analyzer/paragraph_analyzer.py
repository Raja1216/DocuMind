from __future__ import annotations

from src.models.paragraph import Paragraph
from src.models.text_block import TextBlock
from src.analyzer.line_reconstructor import LineReconstructor


class ParagraphAnalyzer:
    """
    Version 1

    One text block = One paragraph.
    """

    @staticmethod
    def analyze(block: TextBlock) -> list[Paragraph]:

        paragraph = Paragraph()

        paragraph.lines.extend(block.lines)
        
        paragraph.text = LineReconstructor.reconstruct(
            block.lines
        )
        
        return [paragraph]