from __future__ import annotations

import unittest

from src.utils.rectangle_union import (
    RectangleUnion,
)


class RectangleUnionTests(
    unittest.TestCase
):

    def test_non_overlapping_rectangles(
        self,
    ) -> None:
        area = RectangleUnion.union_area([
            (
                0.0,
                0.0,
                10.0,
                10.0,
            ),
            (
                20.0,
                0.0,
                30.0,
                10.0,
            ),
        ])

        self.assertEqual(
            area,
            200.0,
        )

    def test_overlapping_rectangles(
        self,
    ) -> None:
        area = RectangleUnion.union_area([
            (
                0.0,
                0.0,
                10.0,
                10.0,
            ),
            (
                5.0,
                5.0,
                15.0,
                15.0,
            ),
        ])

        # 100 + 100 - 25
        self.assertEqual(
            area,
            175.0,
        )

    def test_duplicate_rectangles_count_once(
        self,
    ) -> None:
        area = RectangleUnion.union_area([
            (
                0.0,
                0.0,
                10.0,
                10.0,
            ),
            (
                0.0,
                0.0,
                10.0,
                10.0,
            ),
        ])

        self.assertEqual(
            area,
            100.0,
        )

    def test_rectangles_are_clipped(
        self,
    ) -> None:
        area = RectangleUnion.union_area(
            rectangles=[
                (
                    -10.0,
                    -10.0,
                    20.0,
                    20.0,
                ),
            ],
            clip=(
                0.0,
                0.0,
                10.0,
                10.0,
            ),
        )

        self.assertEqual(
            area,
            100.0,
        )

    def test_coverage_is_clamped(
        self,
    ) -> None:
        coverage = (
            RectangleUnion.coverage(
                rectangles=[
                    (
                        -100.0,
                        -100.0,
                        200.0,
                        200.0,
                    ),
                ],
                container=(
                    0.0,
                    0.0,
                    100.0,
                    100.0,
                ),
            )
        )

        self.assertEqual(
            coverage,
            1.0,
        )

    def test_invalid_rectangle_is_ignored(
        self,
    ) -> None:
        area = RectangleUnion.union_area([
            None,
            (
                0.0,
                0.0,
                0.0,
                10.0,
            ),
            (
                0.0,
                0.0,
                10.0,
                10.0,
            ),
        ])

        self.assertEqual(
            area,
            100.0,
        )


if __name__ == "__main__":
    unittest.main()