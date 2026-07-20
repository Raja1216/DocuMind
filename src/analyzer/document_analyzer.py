from src.analyzer.document_statistics_analyzer import DocumentStatisticsAnalyzer
from src.analyzer.heading_detector import HeadingDetector
from src.analyzer.paragraph_analyzer import ParagraphAnalyzer
from src.analyzer.paragraph_style_analyzer import ParagraphStyleAnalyzer
from src.analyzer.alignment_analyzer import AlignmentAnalyzer
from src.analyzer.paragraph_region_analyzer import (
    ParagraphRegionAnalyzer,
)
from src.analyzer.page_profile_analyzer import (
    PageProfileAnalyzer,
)
from src.analyzer.document_profile_analyzer import (
    DocumentProfileAnalyzer,
)
from src.analyzer.conversion_policy_resolver import (
    ConversionPolicyResolver,
)
from src.analyzer.layout_region_analyzer import (
    LayoutRegionAnalyzer,
)
from src.analyzer.reading_order_analyzer import (
    ReadingOrderAnalyzer,
)
from src.analyzer.paragraph_alignment_analyzer import (
    ParagraphAlignmentAnalyzer,
)
from src.analyzer.alignment_validation_analyzer import (
    AlignmentValidationAnalyzer,
)

class DocumentAnalyzer:

    @staticmethod
    def analyze(
        document,
    ) -> None:
        DocumentStatisticsAnalyzer.analyze(
            document
        )

        HeadingDetector.detect(
            document
        )

        for page in document.pages:
            for block in page.blocks:
                ParagraphAnalyzer.analyze(
                    block
                )

            ParagraphRegionAnalyzer.analyze_page(
                page
            )

        ParagraphStyleAnalyzer.analyze(
            document
        )
        
        LayoutRegionAnalyzer.analyze(
            document
        )
        
        ReadingOrderAnalyzer.analyze(
            document
        )
        
        ParagraphAlignmentAnalyzer.analyze(
            document
        )

        AlignmentValidationAnalyzer.analyze(
            document
        )

        # Page profiling must run after paragraph regions,
        # tables, vectors and charts have been classified.
        for page in document.pages:
            PageProfileAnalyzer.analyze_page(
                page
            )
        
            # Conversion policy depends on the completed page profile.
            ConversionPolicyResolver.resolve(
                page
            )
        
        # Build the document profile after every page has both a
        # PageProfile and a ConversionPolicy.
        DocumentProfileAnalyzer.analyze(
            document
        )           