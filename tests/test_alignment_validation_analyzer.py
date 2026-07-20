from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.alignment_validation_analyzer import (
    AlignmentValidationAnalyzer,
)
from src.models.alignment_validation import (
    AlignmentValidationCode,
)
from src.models.column_region import (
    ColumnRegion,
)
from src.models.document import Document
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.metadata import PDFMetadata
from src.models.page import Page
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
    ParagraphAlignmentResult,
)
from src.models.reading_order import (
    ReadingOrderEntry,
    ReadingOrderRole,
)


def make_document() -> Document:
    return Document(
        metadata=PDFMetadata()
    )


def make_page(
    number: int = 1,
) -> Page:
    return Page(
        number=number,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        rotation=0,
    )


def add_paragraph(
    page: Page,
    number: int,
    left: float = 50.0,
    top: float = 100.0,
    right: float = 550.0,
    bottom: float = 150.0,
    column_id: int | None = None,
):
    paragraph = SimpleNamespace(
        region_number=number,
        text="Visible paragraph text.",
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        column_id=column_id,
    )

    page.paragraph_regions.append(
        paragraph
    )

    return paragraph


def add_result(
    page: Page,
    number: int,
    alignment: ParagraphAlignment,
    confidence: float = 0.85,
    reference_type: AlignmentReferenceType = (
        AlignmentReferenceType.PAGE_BODY
    ),
    reference_id: int | None = 1,
    paragraph_left: float = 50.0,
    paragraph_top: float = 100.0,
    paragraph_right: float = 550.0,
    paragraph_bottom: float = 150.0,
    reference_left: float = 50.0,
    reference_top: float = 50.0,
    reference_right: float = 550.0,
    reference_bottom: float = 750.0,
    left_gap: float = 0.0,
    right_gap: float = 0.0,
    center_offset: float = 0.0,
    line_count: int = 2,
    last_line_width_ratio: float = 0.60,
    last_line_relative_width: float = 0.70,
):
    result = ParagraphAlignmentResult(
        page_number=page.number,
        paragraph_region_number=number,
        alignment=alignment,
        confidence=confidence,
        reference_type=reference_type,
        reference_id=reference_id,
        paragraph_bbox=Rectangle(
            left=paragraph_left,
            top=paragraph_top,
            right=paragraph_right,
            bottom=paragraph_bottom,
        ),
        reference_bbox=Rectangle(
            left=reference_left,
            top=reference_top,
            right=reference_right,
            bottom=reference_bottom,
        ),
        left_gap=left_gap,
        right_gap=right_gap,
        center_offset=center_offset,
        line_count=line_count,
        last_line_width_ratio=(
            last_line_width_ratio
        ),
        last_line_relative_width=(
            last_line_relative_width
        ),
    )

    page.paragraph_alignment_results.append(
        result
    )

    return result


class AlignmentValidationAnalyzerTests(
    unittest.TestCase
):

    def test_valid_document_passes(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        add_paragraph(
            page=page,
            number=1,
        )

        add_result(
            page=page,
            number=1,
            alignment=(
                ParagraphAlignment.JUSTIFY
            ),
            left_gap=0.0,
            right_gap=0.0,
            line_count=3,
            last_line_width_ratio=0.55,
            last_line_relative_width=0.60,
        )

        document.pages.append(
            page
        )

        report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        self.assertTrue(
            report.passed
        )

        self.assertEqual(
            report.error_count,
            0,
        )

        self.assertEqual(
            report.warning_count,
            0,
        )

        self.assertEqual(
            report.paragraph_count,
            1,
        )

        self.assertEqual(
            report.result_count,
            1,
        )

    def test_missing_result_is_error(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        add_paragraph(
            page=page,
            number=1,
        )

        document.pages.append(
            page
        )

        report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        self.assertFalse(
            report.passed
        )

        self.assertEqual(
            report.error_count,
            1,
        )

        self.assertIn(
            AlignmentValidationCode.MISSING_RESULT,
            [
                issue.code
                for issue in report.issues
            ],
        )

    def test_unknown_and_low_confidence_warn(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        add_paragraph(
            page=page,
            number=1,
        )

        add_result(
            page=page,
            number=1,
            alignment=(
                ParagraphAlignment.UNKNOWN
            ),
            confidence=0.30,
        )

        document.pages.append(
            page
        )

        report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        issue_codes = {
            issue.code
            for issue in report.issues
        }

        self.assertIn(
            AlignmentValidationCode.UNKNOWN_ALIGNMENT,
            issue_codes,
        )

        self.assertIn(
            AlignmentValidationCode.LOW_CONFIDENCE,
            issue_codes,
        )

        self.assertEqual(
            report.unknown_count,
            1,
        )

        self.assertEqual(
            report.low_confidence_count,
            1,
        )

        # Warnings do not make the structural report fail.
        self.assertTrue(
            report.passed
        )

    def test_column_reference_mismatch_warns(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            left=340.0,
            right=560.0,
            column_id=2,
        )

        page.column_regions.extend([
            ColumnRegion(
                column_id=1,
                page_number=1,
                column_index=0,
                bbox=Rectangle(
                    left=50.0,
                    top=80.0,
                    right=270.0,
                    bottom=700.0,
                ),
            ),

            ColumnRegion(
                column_id=2,
                page_number=1,
                column_index=1,
                bbox=Rectangle(
                    left=340.0,
                    top=80.0,
                    right=560.0,
                    bottom=700.0,
                ),
            ),
        ])

        page.reading_order_entries.append(
            ReadingOrderEntry(
                order=1,
                page_number=1,
                paragraph_region_number=1,
                role=ReadingOrderRole.COLUMN,
                bbox=Rectangle(
                    left=340.0,
                    top=100.0,
                    right=560.0,
                    bottom=150.0,
                ),
                column_id=2,
            )
        )

        add_result(
            page=page,
            number=1,
            alignment=(
                ParagraphAlignment.LEFT
            ),
            reference_type=(
                AlignmentReferenceType.PAGE_BODY
            ),
            paragraph_left=340.0,
            paragraph_right=560.0,
            reference_left=50.0,
            reference_right=560.0,
            left_gap=290.0,
            right_gap=0.0,
        )

        document.pages.append(
            page
        )

        report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        self.assertIn(
            AlignmentValidationCode.REFERENCE_MISMATCH,
            {
                issue.code
                for issue in report.issues
            },
        )

        self.assertIsNotNone(
            paragraph
        )

    def test_center_geometry_conflict_warns(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        add_paragraph(
            page=page,
            number=1,
            left=60.0,
            right=260.0,
        )

        add_result(
            page=page,
            number=1,
            alignment=(
                ParagraphAlignment.CENTER
            ),
            paragraph_left=60.0,
            paragraph_right=260.0,
            reference_left=50.0,
            reference_right=550.0,
            left_gap=10.0,
            right_gap=290.0,
            center_offset=-140.0,
        )

        document.pages.append(
            page
        )

        report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        self.assertIn(
            (
                AlignmentValidationCode
                .CENTER_GEOMETRY_CONFLICT
            ),
            {
                issue.code
                for issue in report.issues
            },
        )

    def test_reanalysis_replaces_old_report(
        self,
    ) -> None:
        document = make_document()

        page = make_page()

        add_paragraph(
            page=page,
            number=1,
        )

        add_result(
            page=page,
            number=1,
            alignment=(
                ParagraphAlignment.LEFT
            ),
        )

        document.pages.append(
            page
        )

        first_report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        first_report.error_count = 999

        second_report = (
            AlignmentValidationAnalyzer
            .analyze(
                document
            )
        )

        self.assertIsNot(
            first_report,
            second_report,
        )

        self.assertNotEqual(
            second_report.error_count,
            999,
        )


if __name__ == "__main__":
    unittest.main()