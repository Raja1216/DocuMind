from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.layout_region_analyzer import (
    LayoutRegionAnalyzer,
)
from src.analyzer.page_profile_analyzer import (
    PageProfileAnalyzer,
)
from src.models.document import Document
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.layout_region import (
    LayoutRegion,
    LayoutRegionType,
)
from src.models.metadata import PDFMetadata
from src.models.page import Page


def make_document() -> Document:
    return Document(
        metadata=PDFMetadata()
    )


def make_page(
    number: int,
    width: float = 612.0,
    height: float = 792.0,
) -> Page:
    return Page(
        number=number,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=width,
            bottom=height,
        ),
        rotation=0,
    )


def add_paragraph(
    page: Page,
    number: int,
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    font_size: float = 12.0,
) -> None:
    paragraph = SimpleNamespace(
        region_number=number,
        text=text,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        source_block_numbers=[
            number
        ],
    )

    page.paragraph_regions.append(
        paragraph
    )

    span = SimpleNamespace(
        text=text,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        font_size=font_size,
    )

    line = SimpleNamespace(
        spans=[
            span
        ]
    )

    block = SimpleNamespace(
        number=number,
        lines=[
            line
        ],
    )

    page.blocks.append(
        block
    )


class LayoutRegionAnalyzerTests(
    unittest.TestCase
):

    def test_repeated_header_and_page_number_footer(
        self,
    ) -> None:
        document = make_document()

        for page_number in range(
            1,
            4,
        ):
            page = make_page(
                page_number
            )

            add_paragraph(
                page=page,
                number=1,
                text="Annual Project Report",
                left=50.0,
                top=24.0,
                right=250.0,
                bottom=40.0,
            )

            add_paragraph(
                page=page,
                number=2,
                text=(
                    "This is the main body paragraph "
                    "for the document page."
                ),
                left=50.0,
                top=120.0,
                right=560.0,
                bottom=180.0,
            )

            add_paragraph(
                page=page,
                number=3,
                text=str(
                    page_number
                ),
                left=300.0,
                top=748.0,
                right=312.0,
                bottom=764.0,
            )

            document.pages.append(
                page
            )

        LayoutRegionAnalyzer.analyze(
            document
        )

        for page in document.pages:
            region_types = {
                region.region_type
                for region in page.layout_regions
            }

            self.assertIn(
                LayoutRegionType.HEADER,
                region_types,
            )

            self.assertIn(
                LayoutRegionType.FOOTER,
                region_types,
            )

            self.assertIn(
                LayoutRegionType.PAGE_BODY,
                region_types,
            )

            self.assertEqual(
                len(
                    page.column_regions
                ),
                1,
            )

            profile = (
                PageProfileAnalyzer
                .analyze_page(
                    page
                )
            )

            self.assertTrue(
                profile.has_header
            )

            self.assertTrue(
                profile.has_footer
            )

            self.assertEqual(
                profile.column_count,
                1,
            )

    def test_strong_two_column_layout(
        self,
    ) -> None:
        document = make_document()

        page = make_page(
            1
        )

        # Full-width title should remain in the body region
        # rather than being assigned to one column.
        add_paragraph(
            page=page,
            number=1,
            text=(
                "Full Width Document Heading"
            ),
            left=50.0,
            top=45.0,
            right=560.0,
            bottom=75.0,
            font_size=22.0,
        )

        for index in range(3):
            top = (
                130.0
                + index * 110.0
            )

            add_paragraph(
                page=page,
                number=2 + index,
                text=(
                    "Left column paragraph with enough "
                    "text for reliable column detection."
                ),
                left=50.0,
                top=top,
                right=270.0,
                bottom=top + 65.0,
            )

            add_paragraph(
                page=page,
                number=5 + index,
                text=(
                    "Right column paragraph with enough "
                    "text for reliable column detection."
                ),
                left=340.0,
                top=top,
                right=560.0,
                bottom=top + 65.0,
            )

        document.pages.append(
            page
        )

        LayoutRegionAnalyzer.analyze(
            document
        )

        self.assertEqual(
            len(
                page.column_regions
            ),
            2,
        )

        first_column = (
            page.column_regions[0]
        )

        second_column = (
            page.column_regions[1]
        )

        self.assertLess(
            first_column.left,
            second_column.left,
        )

        assigned_paragraph_numbers = {
            paragraph_number
            for column in page.column_regions
            for paragraph_number
            in column.paragraph_region_numbers
        }

        self.assertNotIn(
            1,
            assigned_paragraph_numbers,
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.column_count,
            2,
        )

    def test_vertically_separated_boxes_are_not_columns(
        self,
    ) -> None:
        document = make_document()

        page = make_page(
            1
        )

        for index in range(3):
            top = (
                100.0
                + index * 70.0
            )

            add_paragraph(
                page=page,
                number=1 + index,
                text=(
                    "Upper left content paragraph used "
                    "for geometric testing."
                ),
                left=50.0,
                top=top,
                right=270.0,
                bottom=top + 45.0,
            )

        for index in range(3):
            top = (
                430.0
                + index * 70.0
            )

            add_paragraph(
                page=page,
                number=4 + index,
                text=(
                    "Lower right content paragraph used "
                    "for geometric testing."
                ),
                left=340.0,
                top=top,
                right=560.0,
                bottom=top + 45.0,
            )

        document.pages.append(
            page
        )

        LayoutRegionAnalyzer.analyze(
            document
        )

        # The two groups do not overlap vertically, so they
        # are sequential content boxes rather than columns.
        self.assertEqual(
            len(
                page.column_regions
            ),
            1,
        )

    def test_single_page_top_text_is_not_header(
        self,
    ) -> None:
        document = make_document()

        page = make_page(
            1
        )

        add_paragraph(
            page=page,
            number=1,
            text="Document Title",
            left=180.0,
            top=30.0,
            right=430.0,
            bottom=65.0,
            font_size=28.0,
        )

        add_paragraph(
            page=page,
            number=2,
            text=(
                "Main body content appears beneath "
                "the title."
            ),
            left=50.0,
            top=130.0,
            right=560.0,
            bottom=190.0,
        )

        document.pages.append(
            page
        )

        LayoutRegionAnalyzer.analyze(
            document
        )

        region_types = {
            region.region_type
            for region in page.layout_regions
        }

        self.assertNotIn(
            LayoutRegionType.HEADER,
            region_types,
        )

        self.assertNotIn(
            LayoutRegionType.FOOTER,
            region_types,
        )

    def test_reanalysis_removes_old_regions(
        self,
    ) -> None:
        document = make_document()

        page = make_page(
            1
        )

        add_paragraph(
            page=page,
            number=1,
            text=(
                "A normal body paragraph is present "
                "on this page."
            ),
            left=50.0,
            top=120.0,
            right=560.0,
            bottom=180.0,
        )

        document.pages.append(
            page
        )

        old_region = LayoutRegion(
            region_id=999,
            page_number=1,
            region_type=(
                LayoutRegionType.UNKNOWN
            ),
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=10.0,
                bottom=10.0,
            ),
        )

        page.layout_regions.append(
            old_region
        )

        LayoutRegionAnalyzer.analyze(
            document
        )

        self.assertNotIn(
            999,
            [
                region.region_id
                for region in page.layout_regions
            ],
        )

        self.assertEqual(
            len(
                page.column_regions
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()