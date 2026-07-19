from __future__ import annotations

import unittest

from src.analyzer.conversion_policy_resolver import (
    ConversionPolicyResolver,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page import Page
from src.models.page_profile import (
    ConversionMode,
    PageType,
)


def make_page(
    page_type: PageType,
    recommended_mode: ConversionMode,
    has_text: bool = True,
    requires_ocr: bool = False,
) -> Page:
    page = Page(
        number=1,

        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=612.0,
            bottom=792.0,
        ),

        rotation=0,
    )

    profile = page.profile

    profile.page_type = page_type

    profile.recommended_mode = (
        recommended_mode
    )

    profile.has_extractable_text = (
        has_text
    )

    profile.requires_ocr = (
        requires_ocr
    )

    profile.editable_confidence = 0.80
    profile.fixed_confidence = 0.75
    profile.hybrid_confidence = 0.85
    profile.ocr_confidence = 0.90

    return page


class ConversionPolicyResolverTests(
    unittest.TestCase
):

    def test_simple_text_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=PageType.SIMPLE_TEXT,
            recommended_mode=(
                ConversionMode.EDITABLE
            ),
        )

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.EDITABLE,
        )

        self.assertTrue(
            policy.export_text_as_paragraphs
        )

        self.assertTrue(
            policy.export_lists_as_word_lists
        )

        self.assertFalse(
            policy.run_ocr
        )

        self.assertFalse(
            policy.use_full_page_image
        )

        self.assertEqual(
            policy.confidence,
            0.80,
        )

    def test_low_confidence_text_becomes_hybrid(
        self,
    ) -> None:
        page = make_page(
            page_type=PageType.SIMPLE_TEXT,
            recommended_mode=(
                ConversionMode.EDITABLE
            ),
        )

        page.profile.editable_confidence = (
            0.30
        )

        page.profile.hybrid_confidence = (
            0.70
        )

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.HYBRID,
        )

        self.assertEqual(
            policy.confidence,
            0.70,
        )

        self.assertTrue(
            policy.warnings
        )

    def test_scanned_page_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=PageType.SCANNED,
            recommended_mode=(
                ConversionMode.OCR
            ),
            has_text=False,
            requires_ocr=True,
        )

        page.profile.image_count = 1
        page.profile.image_coverage = 1.0

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.OCR,
        )

        self.assertTrue(
            policy.run_ocr
        )

        self.assertTrue(
            policy.include_ocr_text
        )

        self.assertTrue(
            policy.use_full_page_image
        )

        self.assertFalse(
            policy.export_lists_as_word_lists
        )

    def test_designed_cover_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=(
                PageType.DESIGNED_COVER
            ),
            recommended_mode=(
                ConversionMode.HYBRID
            ),
        )

        page.profile.vector_count = 10

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.HYBRID,
        )

        self.assertTrue(
            policy.export_text_as_paragraphs
        )

        self.assertTrue(
            policy.export_vectors_as_images
        )

        self.assertFalse(
            policy.use_full_page_image
        )

        self.assertTrue(
            policy.allow_region_image_fallback
        )

    def test_table_dominant_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=(
                PageType.TABLE_DOMINANT
            ),
            recommended_mode=(
                ConversionMode.HYBRID
            ),
        )

        page.profile.table_count = 2

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.HYBRID,
        )

        self.assertTrue(
            policy.export_tables_as_word_tables
        )

        self.assertTrue(
            policy.allow_region_image_fallback
        )

    def test_chart_dominant_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=(
                PageType.CHART_DOMINANT
            ),
            recommended_mode=(
                ConversionMode.HYBRID
            ),
        )

        page.profile.chart_count = 2
        page.profile.vector_count = 15

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertTrue(
            policy.export_charts_as_images
        )

        self.assertTrue(
            policy.export_vectors_as_images
        )

        self.assertFalse(
            policy.use_full_page_image
        )

    def test_image_dominant_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=(
                PageType.IMAGE_DOMINANT
            ),
            recommended_mode=(
                ConversionMode.FIXED
            ),
            has_text=False,
        )

        page.profile.image_count = 1

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.FIXED,
        )

        self.assertTrue(
            policy.use_full_page_image
        )

        self.assertFalse(
            policy.export_text_as_paragraphs
        )

        self.assertFalse(
            policy.export_lists_as_word_lists
        )

    def test_form_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=PageType.FORM,
            recommended_mode=(
                ConversionMode.HYBRID
            ),
        )

        page.profile.form_field_count = 4

        policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertEqual(
            policy.mode,
            ConversionMode.HYBRID,
        )

        self.assertTrue(
            policy.export_forms_as_controls
        )

        self.assertTrue(
            policy.export_text_as_paragraphs
        )

    def test_reanalysis_replaces_old_policy(
        self,
    ) -> None:
        page = make_page(
            page_type=PageType.SIMPLE_TEXT,
            recommended_mode=(
                ConversionMode.EDITABLE
            ),
        )

        first_policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        first_policy.add_warning(
            "Temporary warning."
        )

        second_policy = (
            ConversionPolicyResolver
            .resolve(
                page
            )
        )

        self.assertIsNot(
            first_policy,
            second_policy,
        )

        self.assertNotIn(
            "Temporary warning.",
            second_policy.warnings,
        )


if __name__ == "__main__":
    unittest.main()