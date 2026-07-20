from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.paragraph_alignment_analyzer import (
    ParagraphAlignmentAnalyzer,
)
from src.models.column_region import (
    ColumnRegion,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.layout_region import (
    LayoutRegion,
    LayoutRegionType,
)
from src.models.page import Page
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
)


def make_page() -> Page:
    return Page(
        number=1,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        rotation=0,
    )


def make_line(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
):
    return SimpleNamespace(
        text=text,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        spans=[],
    )


def add_paragraph(
    page: Page,
    number: int,
    lines: list,
    layout_region_id: int | None = None,
    column_id: int | None = None,
    list_type: str | None = None,
    list_marker: str | None = None,
    list_marker_left: float | None = None,
    content_left: float | None = None,
):
    left = min(
        line.left
        for line in lines
    )

    top = min(
        line.top
        for line in lines
    )

    right = max(
        line.right
        for line in lines
    )

    bottom = max(
        line.bottom
        for line in lines
    )

    paragraph = SimpleNamespace(
        region_number=number,
        text=" ".join(
            line.text
            for line in lines
        ),
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        lines=lines,
        source_block_numbers=[
            number
        ],
        layout_region_id=(
            layout_region_id
        ),
        column_id=column_id,
        list_type=list_type,
        list_marker=list_marker,
        list_marker_left=(
            list_marker_left
        ),
        list_marker_right=None,
        content_left=content_left,
        detected_alignment=(
            ParagraphAlignment.UNKNOWN
        ),
        alignment_confidence=0.0,
        alignment_reference_type=(
            AlignmentReferenceType.UNKNOWN
        ),
        alignment_reference_id=None,
    )

    page.paragraph_regions.append(
        paragraph
    )

    return paragraph


def add_body_region(
    page: Page,
    region_id: int = 1,
    paragraph_numbers: list[int] | None = None,
    left: float = 50.0,
    top: float = 50.0,
    right: float = 550.0,
    bottom: float = 750.0,
) -> LayoutRegion:
    region = LayoutRegion(
        region_id=region_id,
        page_number=page.number,
        region_type=(
            LayoutRegionType.PAGE_BODY
        ),
        bbox=Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
    )

    region.paragraph_region_numbers.extend(
        paragraph_numbers
        or []
    )

    page.layout_regions.append(
        region
    )

    return region


def add_layout_column(
    page: Page,
    region_id: int,
    parent_region_id: int,
    paragraph_numbers: list[int],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> LayoutRegion:
    region = LayoutRegion(
        region_id=region_id,
        page_number=page.number,
        region_type=(
            LayoutRegionType.COLUMN
        ),
        bbox=Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        parent_region_id=(
            parent_region_id
        ),
    )

    region.paragraph_region_numbers.extend(
        paragraph_numbers
    )

    page.layout_regions.append(
        region
    )

    return region


def add_column(
    page: Page,
    column_id: int,
    column_index: int,
    parent_region_id: int,
    paragraph_numbers: list[int],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> ColumnRegion:
    column = ColumnRegion(
        column_id=column_id,
        page_number=page.number,
        column_index=column_index,
        bbox=Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        parent_region_id=(
            parent_region_id
        ),
    )

    column.paragraph_region_numbers.extend(
        paragraph_numbers
    )

    page.column_regions.append(
        column
    )

    return column


class ParagraphAlignmentAnalyzerTests(
    unittest.TestCase
):

    def test_left_aligned_paragraph(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        paragraph = add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "First left-aligned line.",
                    55.0,
                    100.0,
                    500.0,
                    120.0,
                ),
                make_line(
                    "Second shorter line.",
                    55.0,
                    130.0,
                    420.0,
                    150.0,
                ),
            ],
        )

        results = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].alignment,
            ParagraphAlignment.LEFT,
        )

        self.assertEqual(
            results[0].reference_type,
            AlignmentReferenceType.PAGE_BODY,
        )

        self.assertEqual(
            paragraph.detected_alignment,
            ParagraphAlignment.LEFT,
        )

    def test_centered_single_line_heading(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "Centered Document Heading",
                    180.0,
                    100.0,
                    420.0,
                    130.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.CENTER,
        )

        self.assertGreaterEqual(
            result.confidence,
            0.75,
        )

    def test_right_aligned_paragraph(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "Right-aligned line one.",
                    290.0,
                    100.0,
                    545.0,
                    120.0,
                ),
                make_line(
                    "Right line two.",
                    350.0,
                    130.0,
                    545.0,
                    150.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.RIGHT,
        )
        
        self.assertFalse(
            result.has_hanging_indent
        )
        
        self.assertLessEqual(
            result.right_gap,
            10.0,
        )
        
        self.assertGreater(
            result.left_gap,
            result.right_gap,
        )

    def test_justified_paragraph(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "A full justified line.",
                    52.0,
                    100.0,
                    548.0,
                    120.0,
                ),
                make_line(
                    "Another full justified line.",
                    52.0,
                    130.0,
                    548.0,
                    150.0,
                ),
                make_line(
                    "Short final line.",
                    52.0,
                    160.0,
                    320.0,
                    180.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.JUSTIFY,
        )

        self.assertEqual(
            result.line_count,
            3,
        )

        self.assertLess(
            result.last_line_relative_width,
            0.90,
        )

    def test_alignment_uses_second_column_not_page(
        self,
    ) -> None:
        page = make_page()

        body = add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        add_layout_column(
            page=page,
            region_id=2,
            parent_region_id=(
                body.region_id
            ),
            paragraph_numbers=[],
            left=50.0,
            top=80.0,
            right=270.0,
            bottom=700.0,
        )

        add_layout_column(
            page=page,
            region_id=3,
            parent_region_id=(
                body.region_id
            ),
            paragraph_numbers=[1],
            left=340.0,
            top=80.0,
            right=560.0,
            bottom=700.0,
        )

        add_column(
            page=page,
            column_id=1,
            column_index=0,
            parent_region_id=(
                body.region_id
            ),
            paragraph_numbers=[],
            left=50.0,
            top=80.0,
            right=270.0,
            bottom=700.0,
        )

        add_column(
            page=page,
            column_id=2,
            column_index=1,
            parent_region_id=(
                body.region_id
            ),
            paragraph_numbers=[1],
            left=340.0,
            top=80.0,
            right=560.0,
            bottom=700.0,
        )

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=3,
            column_id=2,
            lines=[
                make_line(
                    "Centered inside right column",
                    380.0,
                    100.0,
                    520.0,
                    125.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertEqual(
            result.reference_type,
            AlignmentReferenceType.COLUMN,
        )

        self.assertEqual(
            result.reference_id,
            2,
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.CENTER,
        )

    def test_footer_uses_full_page_band_width(
        self,
    ) -> None:
        page = make_page()

        footer = LayoutRegion(
            region_id=1,
            page_number=1,
            region_type=(
                LayoutRegionType.FOOTER
            ),
            bbox=Rectangle(
                left=292.0,
                top=740.0,
                right=308.0,
                bottom=765.0,
            ),
        )

        footer.paragraph_region_numbers.append(
            1
        )

        page.layout_regions.append(
            footer
        )

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "1",
                    292.0,
                    744.0,
                    308.0,
                    760.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertEqual(
            result.reference_type,
            AlignmentReferenceType.FOOTER,
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.CENTER,
        )

        self.assertEqual(
            result.reference_bbox.left,
            0.0,
        )

        self.assertEqual(
            result.reference_bbox.right,
            600.0,
        )

    def test_hanging_indent_list_is_left_aligned(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        result = None

        add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            list_type="bullet",
            list_marker="•",
            list_marker_left=55.0,
            content_left=80.0,
            lines=[
                make_line(
                    "• First list line.",
                    55.0,
                    100.0,
                    500.0,
                    120.0,
                ),
                make_line(
                    "Wrapped list content.",
                    80.0,
                    130.0,
                    500.0,
                    150.0,
                ),
            ],
        )

        result = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )[0]
        )

        self.assertTrue(
            result.has_hanging_indent
        )

        self.assertEqual(
            result.alignment,
            ParagraphAlignment.LEFT,
        )

    def test_reanalysis_replaces_old_results(
        self,
    ) -> None:
        page = make_page()

        add_body_region(
            page=page,
            paragraph_numbers=[1],
        )

        paragraph = add_paragraph(
            page=page,
            number=1,
            layout_region_id=1,
            lines=[
                make_line(
                    "Centered heading",
                    200.0,
                    100.0,
                    400.0,
                    130.0,
                ),
            ],
        )

        first_results = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )
        )

        first_results[0].confidence = 0.01

        second_results = (
            ParagraphAlignmentAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            len(second_results),
            1,
        )

        self.assertNotEqual(
            second_results[0].confidence,
            0.01,
        )

        self.assertEqual(
            paragraph.detected_alignment,
            ParagraphAlignment.CENTER,
        )


if __name__ == "__main__":
    unittest.main()