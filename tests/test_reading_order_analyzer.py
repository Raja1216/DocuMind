from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.reading_order_analyzer import (
    ReadingOrderAnalyzer,
)
from src.models.column_region import (
    ColumnRegion,
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
from src.models.reading_order import (
    ReadingDirection,
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
            right=612.0,
            bottom=792.0,
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
) -> None:
    page.paragraph_regions.append(
        SimpleNamespace(
            region_number=number,
            text=text,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            source_block_numbers=[
                number
            ],
            reading_order=None,
            layout_region_id=None,
            column_id=None,
        )
    )


def add_layout_region(
    page: Page,
    region_id: int,
    region_type: LayoutRegionType,
    paragraph_numbers: list[int],
    left: float,
    top: float,
    right: float,
    bottom: float,
    parent_region_id: int | None = None,
) -> LayoutRegion:
    region = LayoutRegion(
        region_id=region_id,
        page_number=page.number,
        region_type=region_type,
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
    paragraph_numbers: list[int],
    left: float,
    top: float,
    right: float,
    bottom: float,
    parent_region_id: int,
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


class ReadingOrderAnalyzerTests(
    unittest.TestCase
):

    def test_header_body_footer_order(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "Repeated Header",
            50.0,
            20.0,
            250.0,
            40.0,
        )

        add_paragraph(
            page,
            2,
            "First body paragraph.",
            50.0,
            120.0,
            560.0,
            170.0,
        )

        add_paragraph(
            page,
            3,
            "Second body paragraph.",
            50.0,
            200.0,
            560.0,
            250.0,
        )

        add_paragraph(
            page,
            4,
            "1",
            300.0,
            748.0,
            312.0,
            764.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.HEADER
            ),
            paragraph_numbers=[1],
            left=47.0,
            top=17.0,
            right=253.0,
            bottom=43.0,
        )

        add_layout_region(
            page=page,
            region_id=2,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[
                2,
                3,
            ],
            left=47.0,
            top=117.0,
            right=563.0,
            bottom=253.0,
        )

        add_layout_region(
            page=page,
            region_id=3,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                2,
                3,
            ],
            left=47.0,
            top=117.0,
            right=563.0,
            bottom=253.0,
            parent_region_id=2,
        )

        add_column(
            page=page,
            column_id=1,
            column_index=0,
            paragraph_numbers=[
                2,
                3,
            ],
            left=47.0,
            top=117.0,
            right=563.0,
            bottom=253.0,
            parent_region_id=2,
        )

        add_layout_region(
            page=page,
            region_id=4,
            region_type=(
                LayoutRegionType.FOOTER
            ),
            paragraph_numbers=[4],
            left=297.0,
            top=745.0,
            right=315.0,
            bottom=767.0,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            [
                entry.paragraph_region_number
                for entry
                in page.reading_order_entries
            ],
            [
                1,
                2,
                3,
                4,
            ],
        )

        self.assertEqual(
            [
                entry.role
                for entry
                in page.reading_order_entries
            ],
            [
                ReadingOrderRole.HEADER,
                ReadingOrderRole.BODY,
                ReadingOrderRole.BODY,
                ReadingOrderRole.FOOTER,
            ],
        )

    def test_full_width_heading_precedes_columns(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "Full Width Heading",
            50.0,
            60.0,
            560.0,
            90.0,
        )

        add_paragraph(
            page,
            2,
            "Left column first paragraph.",
            50.0,
            130.0,
            270.0,
            180.0,
        )

        add_paragraph(
            page,
            3,
            "Left column second paragraph.",
            50.0,
            210.0,
            270.0,
            260.0,
        )

        add_paragraph(
            page,
            4,
            "Right column first paragraph.",
            340.0,
            130.0,
            560.0,
            180.0,
        )

        add_paragraph(
            page,
            5,
            "Right column second paragraph.",
            340.0,
            210.0,
            560.0,
            260.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[
                1,
                2,
                3,
                4,
                5,
            ],
            left=47.0,
            top=57.0,
            right=563.0,
            bottom=263.0,
        )

        add_layout_region(
            page=page,
            region_id=2,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                2,
                3,
            ],
            left=47.0,
            top=127.0,
            right=273.0,
            bottom=263.0,
            parent_region_id=1,
        )

        add_layout_region(
            page=page,
            region_id=3,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                4,
                5,
            ],
            left=337.0,
            top=127.0,
            right=563.0,
            bottom=263.0,
            parent_region_id=1,
        )

        add_column(
            page=page,
            column_id=1,
            column_index=0,
            paragraph_numbers=[
                2,
                3,
            ],
            left=47.0,
            top=127.0,
            right=273.0,
            bottom=263.0,
            parent_region_id=1,
        )

        add_column(
            page=page,
            column_id=2,
            column_index=1,
            paragraph_numbers=[
                4,
                5,
            ],
            left=337.0,
            top=127.0,
            right=563.0,
            bottom=263.0,
            parent_region_id=1,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            [
                entry.paragraph_region_number
                for entry
                in page.reading_order_entries
            ],
            [
                1,
                2,
                3,
                4,
                5,
            ],
        )

        self.assertEqual(
            page.reading_order_entries[0].role,
            ReadingOrderRole.BODY_SPANNING,
        )

    def test_spanning_heading_divides_column_sections(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "Left upper paragraph.",
            50.0,
            100.0,
            270.0,
            150.0,
        )

        add_paragraph(
            page,
            2,
            "Right upper paragraph.",
            340.0,
            100.0,
            560.0,
            150.0,
        )

        add_paragraph(
            page,
            3,
            "Full Width Middle Heading",
            50.0,
            220.0,
            560.0,
            250.0,
        )

        add_paragraph(
            page,
            4,
            "Left lower paragraph.",
            50.0,
            300.0,
            270.0,
            350.0,
        )

        add_paragraph(
            page,
            5,
            "Right lower paragraph.",
            340.0,
            300.0,
            560.0,
            350.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[
                1,
                2,
                3,
                4,
                5,
            ],
            left=47.0,
            top=97.0,
            right=563.0,
            bottom=353.0,
        )

        add_layout_region(
            page=page,
            region_id=2,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                1,
                4,
            ],
            left=47.0,
            top=97.0,
            right=273.0,
            bottom=353.0,
            parent_region_id=1,
        )

        add_layout_region(
            page=page,
            region_id=3,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                2,
                5,
            ],
            left=337.0,
            top=97.0,
            right=563.0,
            bottom=353.0,
            parent_region_id=1,
        )

        add_column(
            page=page,
            column_id=1,
            column_index=0,
            paragraph_numbers=[
                1,
                4,
            ],
            left=47.0,
            top=97.0,
            right=273.0,
            bottom=353.0,
            parent_region_id=1,
        )

        add_column(
            page=page,
            column_id=2,
            column_index=1,
            paragraph_numbers=[
                2,
                5,
            ],
            left=337.0,
            top=97.0,
            right=563.0,
            bottom=353.0,
            parent_region_id=1,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            [
                entry.paragraph_region_number
                for entry
                in page.reading_order_entries
            ],
            [
                1,
                2,
                3,
                4,
                5,
            ],
        )

        middle_entry = (
            page.reading_order_entries[2]
        )

        self.assertEqual(
            middle_entry.role,
            ReadingOrderRole.BODY_SPANNING,
        )

    def test_right_to_left_columns(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "نص العمود الأيسر الأول",
            50.0,
            100.0,
            270.0,
            150.0,
        )

        add_paragraph(
            page,
            2,
            "نص العمود الأيسر الثاني",
            50.0,
            200.0,
            270.0,
            250.0,
        )

        add_paragraph(
            page,
            3,
            "نص العمود الأيمن الأول",
            340.0,
            100.0,
            560.0,
            150.0,
        )

        add_paragraph(
            page,
            4,
            "نص العمود الأيمن الثاني",
            340.0,
            200.0,
            560.0,
            250.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[
                1,
                2,
                3,
                4,
            ],
            left=47.0,
            top=97.0,
            right=563.0,
            bottom=253.0,
        )

        add_layout_region(
            page=page,
            region_id=2,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                1,
                2,
            ],
            left=47.0,
            top=97.0,
            right=273.0,
            bottom=253.0,
            parent_region_id=1,
        )

        add_layout_region(
            page=page,
            region_id=3,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            paragraph_numbers=[
                3,
                4,
            ],
            left=337.0,
            top=97.0,
            right=563.0,
            bottom=253.0,
            parent_region_id=1,
        )

        left_column = add_column(
            page=page,
            column_id=1,
            column_index=0,
            paragraph_numbers=[
                1,
                2,
            ],
            left=47.0,
            top=97.0,
            right=273.0,
            bottom=253.0,
            parent_region_id=1,
        )

        right_column = add_column(
            page=page,
            column_id=2,
            column_index=1,
            paragraph_numbers=[
                3,
                4,
            ],
            left=337.0,
            top=97.0,
            right=563.0,
            bottom=253.0,
            parent_region_id=1,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            page.reading_direction,
            ReadingDirection.RIGHT_TO_LEFT,
        )

        self.assertEqual(
            [
                entry.paragraph_region_number
                for entry
                in page.reading_order_entries
            ],
            [
                3,
                4,
                1,
                2,
            ],
        )

        self.assertEqual(
            right_column.reading_order,
            1,
        )

        self.assertEqual(
            left_column.reading_order,
            2,
        )

    def test_unassigned_paragraph_is_not_lost(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "Body paragraph.",
            50.0,
            100.0,
            560.0,
            150.0,
        )

        add_paragraph(
            page,
            2,
            "Unassigned visual note.",
            400.0,
            400.0,
            560.0,
            430.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[1],
            left=47.0,
            top=97.0,
            right=563.0,
            bottom=153.0,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            [
                entry.paragraph_region_number
                for entry
                in page.reading_order_entries
            ],
            [
                1,
                2,
            ],
        )

        self.assertEqual(
            page.reading_order_entries[1].role,
            ReadingOrderRole.UNASSIGNED,
        )

    def test_reanalysis_replaces_old_order(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page,
            1,
            "Normal body paragraph.",
            50.0,
            100.0,
            560.0,
            150.0,
        )

        add_layout_region(
            page=page,
            region_id=1,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            paragraph_numbers=[1],
            left=47.0,
            top=97.0,
            right=563.0,
            bottom=153.0,
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        page.reading_order_entries[0].order = (
            999
        )

        ReadingOrderAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            page.reading_order_entries[0].order,
            1,
        )

        self.assertEqual(
            len(
                page.reading_order_entries
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()