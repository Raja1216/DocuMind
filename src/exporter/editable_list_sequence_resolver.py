from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.exporter.word_numbering_manager import (
    WordNumberingManager,
)
from src.models.list_item import (
    ListMarkerSource,
)
from src.models.list_sequence import (
    ListSequence,
)
from src.models.page import Page


@dataclass(
    frozen=True,
    slots=True,
)
class EditableListSequenceBinding:
    """
    Connects one ParagraphRegion to one Word numbering
    instance.
    """

    sequence_id: int

    number_id: int

    level: int

    list_type: str

    strip_textual_marker: bool


class EditableListSequenceResolver:
    """
    Creates and reuses one Word numId for every logical
    ListSequence.

    Paragraphs belonging to the same sequence receive the same
    numId and use their detected list_level as w:ilvl.
    """

    MAXIMUM_WORD_LEVEL = 8

    def __init__(
        self,
        numbering_manager: WordNumberingManager,
    ) -> None:
        self.numbering_manager = (
            numbering_manager
        )

        self._number_ids_by_sequence_id: dict[
            int,
            int,
        ] = {}

        self._sequence_indexes_by_page: dict[
            int,
            dict[int, ListSequence],
        ] = {}

    def resolve(
        self,
        page: Page,
        paragraph: Any,
        marker_font_name: str,
        marker_font_size: float,
    ) -> EditableListSequenceBinding | None:
        """
        Resolve one paragraph to its ListSequence and Word
        numbering instance.

        Returns None for legacy list paragraphs that do not yet
        have sequence metadata.
        """

        sequence_id = self._normalize_sequence_id(
            getattr(
                paragraph,
                "list_sequence_id",
                None,
            )
        )

        if sequence_id is None:
            return None

        sequence = self._sequence_index(
            page
        ).get(
            sequence_id
        )

        if sequence is None:
            return None

        number_id = (
            self
            ._number_ids_by_sequence_id
            .get(
                sequence_id
            )
        )

        if number_id is None:
            number_id = (
                self.numbering_manager
                .create_sequence(
                    sequence=sequence,
                    marker_font_name=(
                        marker_font_name
                    ),
                    marker_font_size=(
                        marker_font_size
                    ),
                )
            )

            self._number_ids_by_sequence_id[
                sequence_id
            ] = number_id

        level = self._normalize_level(
            getattr(
                paragraph,
                "list_level",
                0,
            )
        )

        marker_source = (
            self._normalize_marker_source(
                getattr(
                    paragraph,
                    "list_marker_source",
                    ListMarkerSource.UNKNOWN,
                )
            )
        )

        return EditableListSequenceBinding(
            sequence_id=sequence_id,
            number_id=number_id,
            level=level,
            list_type=sequence.list_type,
            strip_textual_marker=(
                marker_source
                == ListMarkerSource.TEXT
            ),
        )

    def number_id_for_sequence(
        self,
        sequence_id: int,
    ) -> int | None:
        """
        Return the Word numId already allocated to a sequence.
        """

        return (
            self
            ._number_ids_by_sequence_id
            .get(
                int(
                    sequence_id
                )
            )
        )

    def _sequence_index(
        self,
        page: Page,
    ) -> dict[int, ListSequence]:
        cache_key = id(
            page
        )

        existing_index = (
            self
            ._sequence_indexes_by_page
            .get(
                cache_key
            )
        )

        if existing_index is not None:
            return existing_index

        sequence_index = {
            int(
                sequence.sequence_id
            ): sequence

            for sequence in getattr(
                page,
                "list_sequences",
                [],
            )
            or []
        }

        self._sequence_indexes_by_page[
            cache_key
        ] = sequence_index

        return sequence_index

    @staticmethod
    def _normalize_sequence_id(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            normalized = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if normalized <= 0:
            return None

        return normalized

    @classmethod
    def _normalize_level(
        cls,
        value: Any,
    ) -> int:
        try:
            level = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            level = 0

        return min(
            max(
                level,
                0,
            ),
            cls.MAXIMUM_WORD_LEVEL,
        )

    @staticmethod
    def _normalize_marker_source(
        value: Any,
    ) -> ListMarkerSource:
        if isinstance(
            value,
            ListMarkerSource,
        ):
            return value

        try:
            return ListMarkerSource(
                str(
                    value
                )
            )

        except ValueError:
            return (
                ListMarkerSource.UNKNOWN
            )