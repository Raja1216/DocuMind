from src.analyzer.document_statistics_analyzer import (
    DocumentStatisticsAnalyzer,
)
from src.analyzer.heading_detector import (
    HeadingDetector,
)
from src.analyzer.paragraph_analyzer import (
    ParagraphAnalyzer,
)
from src.analyzer.paragraph_style_analyzer import (
    ParagraphStyleAnalyzer,
)
from src.analyzer.alignment_analyzer import (
    AlignmentAnalyzer,
)
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
from src.analyzer.list_item_analyzer import (
    ListItemAnalyzer,
)
from src.analyzer.list_sequence_analyzer import (
    ListSequenceAnalyzer,
)
from src.analyzer.page_render_plan_analyzer import (
    PageRenderPlanAnalyzer,
)
from src.analyzer.editable_table_normalizer import (
    EditableTableNormalizer,
)
from src.analyzer.editable_table_grid_reconstructor import (
    EditableTableGridReconstructor,
)
from src.analyzer.editable_table_content_assigner import (
    EditableTableContentAssigner,
)
from src.analyzer.editable_table_merge_detector import (
    EditableTableMergeDetector,
)
from src.analyzer.editable_table_style_analyzer import (
    EditableTableStyleAnalyzer,
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

        # -----------------------------------------------------
        # Block and paragraph-region analysis
        # -----------------------------------------------------

        for page in document.pages:
            for block in page.blocks:
                ParagraphAnalyzer.analyze(
                    block
                )

            ParagraphRegionAnalyzer.analyze_page(
                page
            )

        # -----------------------------------------------------
        # Document-level semantic analysis
        # -----------------------------------------------------

        ParagraphStyleAnalyzer.analyze(
            document
        )

        LayoutRegionAnalyzer.analyze(
            document
        )

        ReadingOrderAnalyzer.analyze(
            document
        )

        ListItemAnalyzer.analyze(
            document
        )

        # This already processes every page.
        ListSequenceAnalyzer.analyze(
            document
        )

        ParagraphAlignmentAnalyzer.analyze(
            document
        )

        AlignmentValidationAnalyzer.analyze(
            document
        )
        EditableTableNormalizer.normalize_document(
            document
        )
        EditableTableGridReconstructor.reconstruct_document(
            document
        )
        EditableTableContentAssigner.assign_document(
            document
        )

        EditableTableMergeDetector.detect_document(
            document
        )
        EditableTableStyleAnalyzer.analyze_document(
            document
        )
        # -----------------------------------------------------
        # Page profile, conversion policy and render plan
        # -----------------------------------------------------

        for page in document.pages:
            # Page profiling must run after paragraphs, tables,
            # images, vectors and charts have been classified.
            PageProfileAnalyzer.analyze_page(
                page
            )

            # Conversion policy depends on the completed page
            # profile.
            ConversionPolicyResolver.resolve(
                page
            )

            # The unified render plan must run after:
            #
            # - paragraph-region analysis
            # - layout and reading-order analysis
            # - list-item and list-sequence analysis
            # - table/image/chart/vector classification
            # - page profiling
            # - conversion policy resolution
            #
            # Running it here also allows PAGE_FALLBACK items
            # to use the resolved conversion policy.
            PageRenderPlanAnalyzer.analyze_page(
                page
            )

        # Build the document profile after every page has a
        # PageProfile and ConversionPolicy.
        DocumentProfileAnalyzer.analyze(
            document
        )