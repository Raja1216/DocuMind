from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.exporter.editable_list_sequence_resolver import (
    EditableListSequenceResolver,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.list_item import (
    ListMarkerKind,
    ListMarkerSource,
)
from src.models.list_sequence import (
    ListContainerType,
    ListSequence,
    ListSequenceItem,
)
from src.models.page import Page


class FakeNumberingManager:
    def __init__(
        self,
    ) -> None:
        self.calls = []
        self.next_number_id = 20

    def create_sequence(
        self,
        sequence,
        marker_font_name: str,
        marker_font_size: float,
    ) -> int:
        self.calls.append({
            "sequence": sequence,
            "font_name": marker_font_name,
            "font_size": marker_font_size,
        })

        number_id = (
            self.next_number_id
        )

        self.next_number_id += 1

        return number_id


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


def make_sequence(
    sequence_id: int,
    list_type: str = "bullet",
) -> ListSequence:
    sequence = ListSequence(
        sequence_id=sequence_id,
        page_number=1,
        list_type=list_type,
        container_type=(
            ListContainerType.PAGE_BODY
        ),
        container_id=1,
        container_left=50.0,
        container_right=550.0,
        maximum_level=1,
    )

    sequence.items.append(
        ListSequenceItem(
            page_number=1,
            paragraph_region_number=1,
            item_index=0,
            level=0,
            marker=(
                "•"
                if list_type == "bullet"
                else "1."
            ),
            marker_kind=(
                ListMarkerKind.BULLET
                if list_type == "bullet"
                else ListMarkerKind.DECIMAL
            ),
            marker_source=(
                ListMarkerSource.TEXT
            ),
            indent=80.0,
            numeric_value=(
                None
                if list_type == "bullet"
                else 1
            ),
        )
    )

    return sequence


def make_paragraph(
    sequence_id: int | None,
    level: int = 0,
    marker_source: ListMarkerSource = (
        ListMarkerSource.TEXT
    ),
):
    return SimpleNamespace(
        list_sequence_id=(
            sequence_id
        ),
        list_level=level,
        list_marker_source=(
            marker_source
        ),
    )


class EditableListSequenceResolverTests(
    unittest.TestCase
):

    def test_same_sequence_reuses_number_id(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.append(
            make_sequence(
                1
            )
        )

        manager = FakeNumberingManager()

        resolver = (
            EditableListSequenceResolver(
                manager
            )
        )

        first = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                level=0,
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        second = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                level=1,
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertIsNotNone(
            first
        )

        self.assertIsNotNone(
            second
        )

        self.assertEqual(
            first.number_id,
            second.number_id,
        )

        self.assertEqual(
            len(
                manager.calls
            ),
            1,
        )

    def test_different_sequences_get_different_ids(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.extend([
            make_sequence(
                1
            ),
            make_sequence(
                2
            ),
        ])

        manager = FakeNumberingManager()

        resolver = (
            EditableListSequenceResolver(
                manager
            )
        )

        first = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        second = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                2
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertNotEqual(
            first.number_id,
            second.number_id,
        )

        self.assertEqual(
            len(
                manager.calls
            ),
            2,
        )

    def test_detected_level_is_preserved(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.append(
            make_sequence(
                1
            )
        )

        resolver = (
            EditableListSequenceResolver(
                FakeNumberingManager()
            )
        )

        binding = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                level=3,
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertEqual(
            binding.level,
            3,
        )

    def test_level_is_capped_at_eight(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.append(
            make_sequence(
                1
            )
        )

        resolver = (
            EditableListSequenceResolver(
                FakeNumberingManager()
            )
        )

        binding = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                level=50,
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertEqual(
            binding.level,
            8,
        )

    def test_textual_marker_is_stripped(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.append(
            make_sequence(
                1
            )
        )

        resolver = (
            EditableListSequenceResolver(
                FakeNumberingManager()
            )
        )

        binding = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                marker_source=(
                    ListMarkerSource.TEXT
                ),
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertTrue(
            binding.strip_textual_marker
        )

    def test_vector_marker_is_not_stripped_from_text(
        self,
    ) -> None:
        page = make_page()

        page.list_sequences.append(
            make_sequence(
                1
            )
        )

        resolver = (
            EditableListSequenceResolver(
                FakeNumberingManager()
            )
        )

        binding = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                1,
                marker_source=(
                    ListMarkerSource.VECTOR
                ),
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertFalse(
            binding.strip_textual_marker
        )

    def test_missing_sequence_returns_none(
        self,
    ) -> None:
        page = make_page()

        resolver = (
            EditableListSequenceResolver(
                FakeNumberingManager()
            )
        )

        result = resolver.resolve(
            page=page,
            paragraph=make_paragraph(
                99
            ),
            marker_font_name="Arial",
            marker_font_size=11.0,
        )

        self.assertIsNone(
            result
        )


if __name__ == "__main__":
    unittest.main()