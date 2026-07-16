from src.analyzer.document_statistics_analyzer import DocumentStatisticsAnalyzer
from src.analyzer.heading_detector import HeadingDetector
from src.analyzer.paragraph_analyzer import ParagraphAnalyzer


class DocumentAnalyzer:

    @staticmethod
    def analyze(document):

        DocumentStatisticsAnalyzer.analyze(document)

        HeadingDetector.detect(document)

        for page in document.pages:
            for block in page.blocks:
                ParagraphAnalyzer.analyze(block)