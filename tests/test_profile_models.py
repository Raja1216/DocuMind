from __future__ import annotations

import unittest

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


class PageProfileModelTests(
    unittest.TestCase
):

    def test_page_creates_profile_automatically(
        self,
    ) -> None:
        page = Page(
            number=3,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),

            rotation=0,
        )

        self.assertEqual(
            page.profile.page_number,
            3,
        )

        self.assertEqual(
            page.profile.page_width,
            612.0,
        )

        self.assertEqual(
            page.profile.page_height,
            792.0,
        )

        self.assertEqual(
            page.profile.rotation,
            0,
        )

        self.assertEqual(
            page.profile.page_type,
            PageType.UNKNOWN,
        )

        self.assertEqual(
            page.profile.recommended_mode,
            ConversionMode.HYBRID,
        )

        self.assertEqual(
            page.profile.page_area,
            612.0 * 792.0,
        )

        self.assertFalse(
            page.profile.is_landscape
        )

        self.assertTrue(
            page.profile.is_portrait
        )

    def test_landscape_page_is_detected(
        self,
    ) -> None:
        page = Page(
            number=1,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=792.0,
                bottom=612.0,
            ),

            rotation=90,
        )

        self.assertTrue(
            page.profile.is_landscape
        )

        self.assertEqual(
            page.profile.rotation,
            90,
        )

    def test_rotation_is_normalized(
        self,
    ) -> None:
        page = Page(
            number=1,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=200.0,
            ),

            rotation=450,
        )

        self.assertEqual(
            page.profile.rotation,
            90,
        )

    def test_page_warning_is_not_duplicated(
        self,
    ) -> None:
        page = Page(
            number=1,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=200.0,
            ),

            rotation=0,
        )

        page.profile.add_warning(
            "OCR may be required."
        )

        page.profile.add_warning(
            "OCR may be required."
        )

        self.assertEqual(
            page.profile.warnings,
            [
                "OCR may be required.",
            ],
        )


class DocumentProfileModelTests(
    unittest.TestCase
):

    def test_document_creates_profile(
        self,
    ) -> None:
        document = Document(
            metadata=PDFMetadata()
        )

        self.assertEqual(
            document.profile.page_count,
            0,
        )

        self.assertEqual(
            document.profile.dominant_page_type,
            PageType.UNKNOWN,
        )

        self.assertEqual(
            document.profile.recommended_mode,
            ConversionMode.HYBRID,
        )

        self.assertFalse(
            document.profile.requires_ocr
        )

    def test_documents_have_separate_profiles(
        self,
    ) -> None:
        first_document = Document(
            metadata=PDFMetadata()
        )

        second_document = Document(
            metadata=PDFMetadata()
        )

        first_document.profile.add_warning(
            "First document warning."
        )

        self.assertEqual(
            first_document.profile.warnings,
            [
                "First document warning.",
            ],
        )

        self.assertEqual(
            second_document.profile.warnings,
            [],
        )


if __name__ == "__main__":
    unittest.main()