from __future__ import annotations

import unittest

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


class LayoutRegionModelTests(
    unittest.TestCase
):

    def test_layout_region_geometry(
        self,
    ) -> None:
        region = LayoutRegion(
            region_id=1,
            page_number=2,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            bbox=Rectangle(
                left=40.0,
                top=50.0,
                right=560.0,
                bottom=740.0,
            ),
        )

        self.assertEqual(
            region.left,
            40.0,
        )

        self.assertEqual(
            region.top,
            50.0,
        )

        self.assertEqual(
            region.right,
            560.0,
        )

        self.assertEqual(
            region.bottom,
            740.0,
        )

        self.assertEqual(
            region.width,
            520.0,
        )

        self.assertEqual(
            region.height,
            690.0,
        )

        self.assertEqual(
            region.center_x,
            300.0,
        )

        self.assertEqual(
            region.center_y,
            395.0,
        )

        self.assertEqual(
            region.area,
            358800.0,
        )

    def test_layout_region_deduplicates_members(
        self,
    ) -> None:
        region = LayoutRegion(
            region_id=1,
            page_number=1,
            region_type=(
                LayoutRegionType.COLUMN
            ),
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=200.0,
            ),
        )

        region.add_child_region(2)
        region.add_child_region(2)

        region.add_paragraph_region(4)
        region.add_paragraph_region(4)

        region.add_source_block(7)
        region.add_source_block(7)

        self.assertEqual(
            region.child_region_ids,
            [2],
        )

        self.assertEqual(
            region.paragraph_region_numbers,
            [4],
        )

        self.assertEqual(
            region.source_block_numbers,
            [7],
        )

    def test_layout_region_confidence_is_clamped(
        self,
    ) -> None:
        region = LayoutRegion(
            region_id=1,
            page_number=1,
            region_type=(
                LayoutRegionType.UNKNOWN
            ),
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=100.0,
            ),
        )

        region.set_confidence(1.50)

        self.assertEqual(
            region.confidence,
            1.0,
        )

        region.set_confidence(-0.25)

        self.assertEqual(
            region.confidence,
            0.0,
        )

    def test_column_region_geometry(
        self,
    ) -> None:
        column = ColumnRegion(
            column_id=1,
            page_number=1,
            column_index=0,
            bbox=Rectangle(
                left=50.0,
                top=100.0,
                right=280.0,
                bottom=700.0,
            ),
        )

        self.assertEqual(
            column.width,
            230.0,
        )

        self.assertEqual(
            column.height,
            600.0,
        )

        self.assertEqual(
            column.center_x,
            165.0,
        )

        self.assertEqual(
            column.center_y,
            400.0,
        )

    def test_column_region_members_are_independent(
        self,
    ) -> None:
        first_column = ColumnRegion(
            column_id=1,
            page_number=1,
            column_index=0,
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=200.0,
            ),
        )

        second_column = ColumnRegion(
            column_id=2,
            page_number=1,
            column_index=1,
            bbox=Rectangle(
                left=120.0,
                top=0.0,
                right=220.0,
                bottom=200.0,
            ),
        )

        first_column.add_paragraph_region(
            10
        )

        self.assertEqual(
            first_column.paragraph_region_numbers,
            [10],
        )

        self.assertEqual(
            second_column.paragraph_region_numbers,
            [],
        )

    def test_page_initializes_empty_layout_lists(
        self,
    ) -> None:
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

        self.assertEqual(
            page.layout_regions,
            [],
        )

        self.assertEqual(
            page.column_regions,
            [],
        )


if __name__ == "__main__":
    unittest.main()