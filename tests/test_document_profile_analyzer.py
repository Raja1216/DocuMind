from __future__ import annotations

import unittest

from src.analyzer.document_profile_analyzer import (
    DocumentProfileAnalyzer,
)
from src.models.document import Document
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.metadata import PDFMetadata
from src.models.page import Page
from src.models.page_profile import (
    ConversionMode,
    PageType,
)


def make_page(
    number: int,
    width: float = 612.0,
    height: float = 792.0,
    page_type: PageType = PageType.SIMPLE_TEXT,
    mode: ConversionMode = ConversionMode.EDITABLE,
    has_text: bool = True,
    requires_ocr: bool = False,
) -> Page:
    """
    Create a Page with an explicitly configured PageProfile.
    """

    page = Page(
        number=number,

        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=width,
            bottom=height,
        ),

        rotation=0,
    )

    page.profile.page_type = page_type
    page.profile.recommended_mode = mode

    page.profile.has_extractable_text = (
        has_text
    )

    page.profile.requires_ocr = (
        requires_ocr
    )

    return page


class DocumentProfileAnalyzerTests(
    unittest.TestCase
):

    def test_all_simple_text_pages(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        document.pages.extend([
            make_page(
                number=1,
            ),
            make_page(
                number=2,
            ),
            make_page(
                number=3,
            ),
        ])

        for page in document.pages:
            page.profile.editable_confidence = 0.80
            page.profile.fixed_confidence = 0.15
            page.profile.hybrid_confidence = 0.60
            page.profile.ocr_confidence = 0.0

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertEqual(
            profile.page_count,
            3,
        )

        self.assertEqual(
            profile.digital_page_count,
            3,
        )

        self.assertEqual(
            profile.scanned_page_count,
            0,
        )

        self.assertEqual(
            profile.dominant_page_type,
            PageType.SIMPLE_TEXT,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.EDITABLE,
        )

        self.assertEqual(
            profile.page_type_counts,
            {
                "simple_text": 3,
            },
        )

        self.assertEqual(
            profile.mode_counts,
            {
                "editable": 3,
            },
        )

        self.assertFalse(
            profile.requires_ocr
        )

        self.assertFalse(
            profile.requires_hybrid_conversion
        )

        self.assertAlmostEqual(
            profile.editable_confidence,
            0.80,
        )

    def test_mixed_digital_and_scanned_document(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        digital_page = make_page(
            number=1,
            page_type=PageType.SIMPLE_TEXT,
            mode=ConversionMode.EDITABLE,
            has_text=True,
            requires_ocr=False,
        )

        scanned_page = make_page(
            number=2,
            page_type=PageType.SCANNED,
            mode=ConversionMode.OCR,
            has_text=False,
            requires_ocr=True,
        )

        scanned_page.profile.image_coverage = (
            1.0
        )

        document.pages.extend([
            digital_page,
            scanned_page,
        ])

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertEqual(
            profile.digital_page_count,
            1,
        )

        self.assertEqual(
            profile.scanned_page_count,
            1,
        )

        # Both page types occur once, so the document-level
        # dominant type is MIXED.
        self.assertEqual(
            profile.dominant_page_type,
            PageType.MIXED,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.HYBRID,
        )

        self.assertTrue(
            profile.contains_scanned_pages
        )

        self.assertTrue(
            profile.contains_digital_pages
        )

        self.assertTrue(
            profile.requires_ocr
        )

        self.assertTrue(
            profile.requires_hybrid_conversion
        )

    def test_multiple_page_sizes_and_orientations(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        document.pages.extend([
            make_page(
                number=1,
                width=612.0,
                height=792.0,
            ),

            # Tiny floating-point differences should still
            # count as the same page size.
            make_page(
                number=2,
                width=612.001,
                height=792.002,
            ),

            make_page(
                number=3,
                width=842.0,
                height=595.0,
            ),
        ])

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertTrue(
            profile.contains_multiple_page_sizes
        )

        self.assertTrue(
            profile.contains_multiple_orientations
        )

        self.assertTrue(
            profile.requires_hybrid_conversion
        )

    def test_feature_flags_are_aggregated(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        table_page = make_page(
            number=1,
            page_type=(
                PageType.TABLE_DOMINANT
            ),
            mode=ConversionMode.HYBRID,
        )

        table_page.profile.table_count = 2

        chart_page = make_page(
            number=2,
            page_type=(
                PageType.CHART_DOMINANT
            ),
            mode=ConversionMode.HYBRID,
        )

        chart_page.profile.chart_count = 1

        form_page = make_page(
            number=3,
            page_type=PageType.FORM,
            mode=ConversionMode.HYBRID,
        )

        form_page.profile.form_field_count = (
            5
        )

        document.pages.extend([
            table_page,
            chart_page,
            form_page,
        ])

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertTrue(
            profile.contains_tables
        )

        self.assertTrue(
            profile.contains_charts
        )

        self.assertTrue(
            profile.contains_forms
        )

        self.assertEqual(
            profile.table_page_count,
            1,
        )

        self.assertEqual(
            profile.chart_page_count,
            1,
        )

        self.assertEqual(
            profile.form_page_count,
            1,
        )

        self.assertTrue(
            profile.requires_hybrid_conversion
        )

    def test_tied_page_types_produce_mixed_dominant_type(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        document.pages.extend([
            make_page(
                number=1,
                page_type=(
                    PageType.SIMPLE_TEXT
                ),
                mode=(
                    ConversionMode.EDITABLE
                ),
            ),
            make_page(
                number=2,
                page_type=(
                    PageType.MULTI_COLUMN
                ),
                mode=(
                    ConversionMode.HYBRID
                ),
            ),
        ])

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertEqual(
            profile.dominant_page_type,
            PageType.MIXED,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.HYBRID,
        )

    def test_empty_document(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertEqual(
            profile.page_count,
            0,
        )

        self.assertEqual(
            profile.dominant_page_type,
            PageType.UNKNOWN,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.HYBRID,
        )

        self.assertTrue(
            profile.warnings
        )

    def test_reanalysis_does_not_keep_old_values(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        document.pages.append(
            make_page(
                number=1,
            )
        )

        first_profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        first_profile.add_warning(
            "Temporary warning."
        )

        second_profile = (
            DocumentProfileAnalyzer
            .analyze(
                document
            )
        )

        self.assertIsNot(
            first_profile,
            second_profile,
        )

        self.assertNotIn(
            "Temporary warning.",
            second_profile.warnings,
        )


if __name__ == "__main__":
    unittest.main()