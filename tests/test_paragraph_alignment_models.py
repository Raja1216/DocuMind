from __future__ import annotations

import unittest

from dataclasses import fields

from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page import Page
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
    ParagraphAlignmentResult,
)
from src.models.paragraph_region import (
    ParagraphRegion,
)


class ParagraphAlignmentModelTests(
    unittest.TestCase
):

    def test_default_alignment_result(
        self,
    ) -> None:
        result = ParagraphAlignmentResult(
            page_number=1,
            paragraph_region_number=3,
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.UNKNOWN,
        )

        self.assertEqual(
            result.reference_type,
            AlignmentReferenceType.UNKNOWN,
        )

        self.assertEqual(
            result.confidence,
            0.0,
        )

        self.assertIsNone(
            result.reference_id
        )

    def test_alignment_geometry_properties(
        self,
    ) -> None:
        result = ParagraphAlignmentResult(
            page_number=1,
            paragraph_region_number=3,

            paragraph_bbox=Rectangle(
                left=100.0,
                top=150.0,
                right=400.0,
                bottom=210.0,
            ),

            reference_bbox=Rectangle(
                left=50.0,
                top=100.0,
                right=550.0,
                bottom=700.0,
            ),

            center_offset=-50.0,
        )

        self.assertEqual(
            result.paragraph_width,
            300.0,
        )

        self.assertEqual(
            result.paragraph_height,
            60.0,
        )

        self.assertEqual(
            result.reference_width,
            500.0,
        )

        self.assertEqual(
            result.absolute_center_offset,
            50.0,
        )

    def test_confidence_is_clamped(
        self,
    ) -> None:
        result = ParagraphAlignmentResult(
            page_number=1,
            paragraph_region_number=1,
        )

        result.set_confidence(
            1.75
        )

        self.assertEqual(
            result.confidence,
            1.0,
        )

        result.set_confidence(
            -0.50
        )

        self.assertEqual(
            result.confidence,
            0.0,
        )

    def test_width_ratios_are_normalized(
        self,
    ) -> None:
        result = ParagraphAlignmentResult(
            page_number=1,
            paragraph_region_number=1,
        )

        result.set_width_ratio(
            1.40
        )

        self.assertEqual(
            result.width_ratio,
            1.0,
        )

        result.set_last_line_width_ratio(
            -0.20
        )

        self.assertEqual(
            result.last_line_width_ratio,
            0.0,
        )

        result.set_last_line_relative_width(
            0.65
        )

        self.assertEqual(
            result.last_line_relative_width,
            0.65,
        )

    def test_reasons_and_warnings_are_deduplicated(
        self,
    ) -> None:
        result = ParagraphAlignmentResult(
            page_number=1,
            paragraph_region_number=1,
        )

        result.add_reason(
            "Balanced container gaps."
        )

        result.add_reason(
            "Balanced container gaps."
        )

        result.add_warning(
            "Low line count."
        )

        result.add_warning(
            "Low line count."
        )

        self.assertEqual(
            result.reasons,
            [
                "Balanced container gaps.",
            ],
        )

        self.assertEqual(
            result.warnings,
            [
                "Low line count.",
            ],
        )

    def test_paragraph_region_contains_alignment_fields(
        self,
    ) -> None:
        paragraph_field_names = {
            field.name
            for field in fields(
                ParagraphRegion
            )
        }

        self.assertIn(
            "detected_alignment",
            paragraph_field_names,
        )

        self.assertIn(
            "alignment_confidence",
            paragraph_field_names,
        )

        self.assertIn(
            "alignment_reference_type",
            paragraph_field_names,
        )

        self.assertIn(
            "alignment_reference_id",
            paragraph_field_names,
        )

    def test_page_has_independent_alignment_results(
        self,
    ) -> None:
        first_page = Page(
            number=1,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),

            rotation=0,
        )

        second_page = Page(
            number=2,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),

            rotation=0,
        )

        first_page.paragraph_alignment_results.append(
            ParagraphAlignmentResult(
                page_number=1,
                paragraph_region_number=1,
                alignment=(
                    ParagraphAlignment.LEFT
                ),
            )
        )

        self.assertEqual(
            len(
                first_page
                .paragraph_alignment_results
            ),
            1,
        )

        self.assertEqual(
            second_page
            .paragraph_alignment_results,
            [],
        )


if __name__ == "__main__":
    unittest.main()