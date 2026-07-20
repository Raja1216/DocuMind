from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.list_item_analyzer import (
    ListItemAnalyzer,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.list_item import (
    ListMarkerKind,
    ListMarkerSource,
)
from src.models.page import Page


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


def make_span(
    text: str,
    left: float,
    right: float,
):
    return SimpleNamespace(
        text=text,
        left=left,
        top=100.0,
        right=right,
        bottom=115.0,
        font_size=11.0,
    )


def add_paragraph(
    page: Page,
    number: int,
    spans: list,
):
    paragraph = SimpleNamespace(
        region_number=number,
        text="".join(
            span.text
            for span in spans
        ),
        left=min(
            span.left
            for span in spans
        ),
        top=100.0,
        right=max(
            span.right
            for span in spans
        ),
        bottom=115.0,
        lines=[
            SimpleNamespace(
                spans=spans
            )
        ],
        list_type=None,
        list_marker=None,
        list_level=0,
        list_marker_kind=(
            ListMarkerKind.UNKNOWN
        ),
        list_marker_source=(
            ListMarkerSource.UNKNOWN
        ),
        list_confidence=0.0,
        content_left=None,
        list_marker_left=None,
        list_marker_right=None,
    )

    page.paragraph_regions.append(
        paragraph
    )

    return paragraph


class ListItemAnalyzerTests(
    unittest.TestCase
):

    def test_textual_bullet_is_detected(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "•",
                    50.0,
                    56.0,
                ),
                make_span(
                    " First item",
                    70.0,
                    180.0,
                ),
            ],
        )

        results = (
            ListItemAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            paragraph.list_type,
            "bullet",
        )

        self.assertEqual(
            paragraph.list_marker,
            "•",
        )

        self.assertEqual(
            paragraph.list_marker_source,
            ListMarkerSource.TEXT,
        )

        self.assertEqual(
            paragraph.list_marker_kind,
            ListMarkerKind.BULLET,
        )

        self.assertEqual(
            paragraph.content_left,
            70.0,
        )

    def test_decimal_number_is_detected(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "1.",
                    50.0,
                    62.0,
                ),
                make_span(
                    " First item",
                    75.0,
                    180.0,
                ),
            ],
        )

        ListItemAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            paragraph.list_type,
            "number",
        )

        self.assertEqual(
            paragraph.list_marker_kind,
            ListMarkerKind.DECIMAL,
        )

    def test_multilevel_decimal_is_detected(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "1.2.",
                    70.0,
                    92.0,
                ),
                make_span(
                    " Nested item",
                    105.0,
                    220.0,
                ),
            ],
        )

        ListItemAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            paragraph.list_marker_kind,
            (
                ListMarkerKind
                .MULTILEVEL_DECIMAL
            ),
        )

    def test_alphabetic_marker_is_detected(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "a)",
                    50.0,
                    62.0,
                ),
                make_span(
                    " Alphabetic item",
                    75.0,
                    200.0,
                ),
            ],
        )

        ListItemAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            paragraph.list_type,
            "number",
        )

        self.assertEqual(
            paragraph.list_marker_kind,
            ListMarkerKind.LOWER_ALPHA,
        )

    def test_vector_bullet_is_preserved(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "Vector bullet content",
                    80.0,
                    230.0,
                ),
            ],
        )

        paragraph.list_type = "bullet"
        paragraph.list_marker = "•"
        paragraph.list_marker_left = 55.0
        paragraph.list_marker_right = 61.0
        paragraph.content_left = 80.0

        ListItemAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            paragraph.list_marker_source,
            ListMarkerSource.VECTOR,
        )

        self.assertEqual(
            paragraph.content_left,
            80.0,
        )

    def test_normal_paragraph_is_not_list(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "Normal paragraph.",
                    50.0,
                    180.0,
                ),
            ],
        )

        results = (
            ListItemAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            results,
            [],
        )

        self.assertIsNone(
            paragraph.list_type
        )

    def test_reanalysis_removes_stale_list_data(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            number=1,
            spans=[
                make_span(
                    "• First item",
                    50.0,
                    180.0,
                ),
            ],
        )

        ListItemAnalyzer.analyze_page(
            page
        )

        paragraph.lines[0].spans[0].text = (
            "Normal paragraph."
        )

        paragraph.text = (
            "Normal paragraph."
        )

        ListItemAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            page.list_item_results,
            [],
        )

        self.assertIsNone(
            paragraph.list_type
        )


if __name__ == "__main__":
    unittest.main()