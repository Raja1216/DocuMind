from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.list_sequence_analyzer import (
    ListSequenceAnalyzer,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.list_item import (
    ListMarkerKind,
    ListMarkerSource,
)
from src.models.page import Page
from src.models.reading_order import (
    ReadingOrderEntry,
    ReadingOrderRole,
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


def add_paragraph(
    page: Page,
    number: int,
    text: str,
    top: float,
    content_left: float,
    list_type: str | None = "bullet",
    marker: str | None = "•",
    marker_kind: ListMarkerKind = (
        ListMarkerKind.BULLET
    ),
):
    paragraph = SimpleNamespace(
        region_number=number,
        text=text,
        left=content_left,
        top=top,
        right=500.0,
        bottom=top + 18.0,
        lines=[],
        column_id=None,
        layout_region_id=None,
        list_type=list_type,
        list_marker=marker,
        list_level=0,
        list_marker_kind=marker_kind,
        list_marker_source=(
            ListMarkerSource.TEXT
        ),
        list_confidence=(
            0.95
            if list_type is not None
            else 0.0
        ),
        list_marker_left=(
            content_left - 15.0
            if list_type is not None
            else None
        ),
        list_marker_right=(
            content_left - 5.0
            if list_type is not None
            else None
        ),
        content_left=(
            content_left
            if list_type is not None
            else None
        ),
        list_sequence_id=None,
        list_item_index=None,
    )

    page.paragraph_regions.append(
        paragraph
    )

    page.reading_order_entries.append(
        ReadingOrderEntry(
            order=number,
            page_number=page.number,
            paragraph_region_number=number,
            role=ReadingOrderRole.BODY,
            bbox=Rectangle(
                left=paragraph.left,
                top=paragraph.top,
                right=paragraph.right,
                bottom=paragraph.bottom,
            ),
        )
    )

    return paragraph


class ListSequenceAnalyzerTests(
    unittest.TestCase
):

    def test_consecutive_bullets_form_one_sequence(
        self,
    ) -> None:
        page = make_page()

        first = add_paragraph(
            page,
            1,
            "• First",
            100.0,
            80.0,
        )

        second = add_paragraph(
            page,
            2,
            "• Second",
            125.0,
            80.0,
        )

        next_id = (
            ListSequenceAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            len(page.list_sequences),
            1,
        )

        self.assertEqual(
            len(
                page.list_sequences[0].items
            ),
            2,
        )

        self.assertEqual(
            first.list_sequence_id,
            second.list_sequence_id,
        )

        self.assertEqual(
            next_id,
            2,
        )

    def test_normal_paragraph_splits_lists(
        self,
    ) -> None:
        page = make_page()

        first = add_paragraph(
            page,
            1,
            "• First list",
            100.0,
            80.0,
        )

        add_paragraph(
            page,
            2,
            "Normal paragraph",
            130.0,
            50.0,
            list_type=None,
            marker=None,
            marker_kind=(
                ListMarkerKind.UNKNOWN
            ),
        )

        second = add_paragraph(
            page,
            3,
            "• Second list",
            170.0,
            80.0,
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.list_sequences),
            2,
        )

        self.assertNotEqual(
            first.list_sequence_id,
            second.list_sequence_id,
        )

    def test_indentation_creates_nested_level(
        self,
    ) -> None:
        page = make_page()

        first = add_paragraph(
            page,
            1,
            "• Parent",
            100.0,
            80.0,
        )

        nested = add_paragraph(
            page,
            2,
            "◦ Child",
            125.0,
            115.0,
        )

        third = add_paragraph(
            page,
            3,
            "• Parent again",
            150.0,
            80.0,
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            first.list_level,
            0,
        )

        self.assertEqual(
            nested.list_level,
            1,
        )

        self.assertEqual(
            third.list_level,
            0,
        )

        self.assertEqual(
            page.list_sequences[0]
            .maximum_level,
            1,
        )

    def test_multilevel_marker_sets_explicit_level(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page,
            1,
            "1.2. Nested item",
            100.0,
            80.0,
            list_type="number",
            marker="1.2.",
            marker_kind=(
                ListMarkerKind
                .MULTILEVEL_DECIMAL
            ),
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            paragraph.list_level,
            1,
        )

    def test_numbering_restart_creates_new_sequence(
        self,
    ) -> None:
        page = make_page()

        first = add_paragraph(
            page,
            1,
            "1. First",
            100.0,
            80.0,
            list_type="number",
            marker="1.",
            marker_kind=(
                ListMarkerKind.DECIMAL
            ),
        )

        add_paragraph(
            page,
            2,
            "2. Second",
            125.0,
            80.0,
            list_type="number",
            marker="2.",
            marker_kind=(
                ListMarkerKind.DECIMAL
            ),
        )

        restarted = add_paragraph(
            page,
            3,
            "1. Restart",
            150.0,
            80.0,
            list_type="number",
            marker="1.",
            marker_kind=(
                ListMarkerKind.DECIMAL
            ),
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.list_sequences),
            2,
        )

        self.assertNotEqual(
            first.list_sequence_id,
            restarted.list_sequence_id,
        )

    def test_large_vertical_gap_splits_sequence(
        self,
    ) -> None:
        page = make_page()

        first = add_paragraph(
            page,
            1,
            "• First",
            100.0,
            80.0,
        )

        second = add_paragraph(
            page,
            2,
            "• Distant",
            250.0,
            80.0,
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.list_sequences),
            2,
        )

        self.assertNotEqual(
            first.list_sequence_id,
            second.list_sequence_id,
        )

    def test_reanalysis_replaces_stale_sequences(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page,
            1,
            "• First",
            100.0,
            80.0,
        )

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.list_sequences),
            1,
        )

        paragraph.list_type = None
        paragraph.list_confidence = 0.0

        ListSequenceAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            page.list_sequences,
            [],
        )

        self.assertIsNone(
            paragraph.list_sequence_id
        )

        self.assertIsNone(
            paragraph.list_item_index
        )


if __name__ == "__main__":
    unittest.main()