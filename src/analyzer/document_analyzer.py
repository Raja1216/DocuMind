from __future__ import annotations

from src.analyzer.paragraph_analyzer import ParagraphAnalyzer
from src.models.document import Document
from src.analyzer.heading_detector import HeadingDetector
from src.analyzer.document_statistics_analyzer import (
    DocumentStatisticsAnalyzer,
)


class DocumentAnalyzer:
    """
    Runs all analysis passes on the document.
    """

    @staticmethod
    def analyze(document: Document) -> None:
        DocumentStatisticsAnalyzer.analyze(document)

        for page in document.pages:
            HeadingDetector.detect(page)

            for block in page.blocks:

                ParagraphAnalyzer.analyze(block)