from __future__ import annotations

import re

from dataclasses import dataclass
from statistics import fmean, median
from typing import Any

from src.models.document import Document
from src.models.layout_region import (
    LayoutRegionType,
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
from src.utils.rectangle_union import (
    RectangleUnion,
)


@dataclass(slots=True)
class _OrderedParagraph:
    paragraph: Any
    paragraph_number: int
    order: int
    top: float
    left: float


@dataclass(slots=True)
class _ContainerReference:
    container_type: ListContainerType
    container_id: int | None
    left: float
    right: float

    @property
    def width(self) -> float:
        return max(
            self.right - self.left,
            1.0,
        )

    @property
    def key(
        self,
    ) -> tuple[
        ListContainerType,
        int | None,
    ]:
        return (
            self.container_type,
            self.container_id,
        )


class ListSequenceAnalyzer:
    """
    Groups detected list items and infers nesting levels.

    Grouping is based on:

        reading order;
        intervening normal paragraphs;
        containing column/body region;
        list type;
        vertical distance;
        numbering restarts.

    Nesting is measured relative to the containing region,
    never relative to the complete page.
    """

    MINIMUM_LIST_CONFIDENCE = 0.55

    MINIMUM_INDENT_CLUSTER_TOLERANCE = 8.0
    INDENT_CLUSTER_CONTAINER_RATIO = 0.018

    MINIMUM_SEQUENCE_GAP = 36.0
    LINE_HEIGHT_GAP_FACTOR = 3.0

    MAXIMUM_WORD_LIST_LEVEL = 8

    DECIMAL_VALUE_PATTERN = re.compile(
        r"^\d+$"
    )

    MULTILEVEL_VALUE_PATTERN = re.compile(
        r"^\d+(?:\.\d+)+$"
    )

    ROMAN_VALUE_PATTERN = re.compile(
        r"^[ivxlcdm]+$",
        flags=re.IGNORECASE,
    )

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> None:
        next_sequence_id = 1

        for page in document.pages:
            next_sequence_id = (
                cls.analyze_page(
                    page=page,
                    starting_sequence_id=(
                        next_sequence_id
                    ),
                )
            )

    @classmethod
    def analyze_page(
        cls,
        page: Page,
        starting_sequence_id: int = 1,
    ) -> int:
        """
        Rebuild list sequences on one page.

        Returns the next unused document-level sequence ID.
        """

        page.list_sequences.clear()

        for paragraph in (
            page.paragraph_regions
        ):
            paragraph.list_sequence_id = None
            paragraph.list_item_index = None

            # ListItemAnalyzer sets level 0 initially.
            paragraph.list_level = 0

        ordered_paragraphs = (
            cls._collect_ordered_paragraphs(
                page
            )
        )

        provisional_groups: list[
            list[_OrderedParagraph]
        ] = []

        active_group: list[
            _OrderedParagraph
        ] = []

        active_container: (
            _ContainerReference | None
        ) = None

        previous_record: (
            _OrderedParagraph | None
        ) = None

        for record in ordered_paragraphs:
            paragraph = record.paragraph

            if not cls._is_list_item(
                paragraph
            ):
                cls._flush_group(
                    active_group=active_group,
                    destination=(
                        provisional_groups
                    ),
                )

                active_group = []
                active_container = None
                previous_record = None
                continue

            current_container = (
                cls._resolve_container(
                    page=page,
                    paragraph=paragraph,
                )
            )

            if not active_group:
                active_group = [
                    record
                ]

                active_container = (
                    current_container
                )

                previous_record = record
                continue

            assert active_container is not None
            assert previous_record is not None

            should_continue = (
                cls._can_continue_sequence(
                    previous_record=(
                        previous_record
                    ),
                    current_record=record,
                    previous_container=(
                        active_container
                    ),
                    current_container=(
                        current_container
                    ),
                )
            )

            if should_continue:
                active_group.append(
                    record
                )

            else:
                cls._flush_group(
                    active_group=active_group,
                    destination=(
                        provisional_groups
                    ),
                )

                active_group = [
                    record
                ]

                active_container = (
                    current_container
                )

            previous_record = record

        cls._flush_group(
            active_group=active_group,
            destination=provisional_groups,
        )

        next_sequence_id = (
            starting_sequence_id
        )

        for provisional_group in (
            provisional_groups
        ):
            split_groups = (
                cls._split_numbering_restarts(
                    provisional_group
                )
            )

            for group in split_groups:
                if not group:
                    continue

                sequence = (
                    cls._build_sequence(
                        page=page,
                        records=group,
                        sequence_id=(
                            next_sequence_id
                        ),
                    )
                )

                page.list_sequences.append(
                    sequence
                )

                next_sequence_id += 1

        return next_sequence_id

    # ---------------------------------------------------------
    # Grouping
    # ---------------------------------------------------------

    @staticmethod
    def _flush_group(
        active_group: list[
            _OrderedParagraph
        ],
        destination: list[
            list[_OrderedParagraph]
        ],
    ) -> None:
        if active_group:
            destination.append(
                list(
                    active_group
                )
            )

    @classmethod
    def _can_continue_sequence(
        cls,
        previous_record: _OrderedParagraph,
        current_record: _OrderedParagraph,
        previous_container: _ContainerReference,
        current_container: _ContainerReference,
    ) -> bool:
        previous = (
            previous_record.paragraph
        )

        current = (
            current_record.paragraph
        )

        if (
            previous_container.key
            != current_container.key
        ):
            return False

        if (
            previous.list_type
            != current.list_type
        ):
            return False

        vertical_gap = max(
            float(
                getattr(
                    current,
                    "top",
                    current_record.top,
                )
            )
            - float(
                getattr(
                    previous,
                    "bottom",
                    previous_record.top,
                )
            ),
            0.0,
        )

        reference_line_height = max(
            cls._estimate_line_height(
                previous
            ),
            cls._estimate_line_height(
                current
            ),
            1.0,
        )

        maximum_gap = max(
            cls.MINIMUM_SEQUENCE_GAP,
            reference_line_height
            * cls.LINE_HEIGHT_GAP_FACTOR,
        )

        if vertical_gap > maximum_gap:
            return False

        return True

    @classmethod
    def _split_numbering_restarts(
        cls,
        records: list[
            _OrderedParagraph
        ],
    ) -> list[
        list[_OrderedParagraph]
    ]:
        """
        Split clear top-level numbering restarts.

        Example:

            1. First
            2. Second
            1. Separate list
        """

        if not records:
            return []

        if (
            records[0].paragraph.list_type
            != "number"
        ):
            return [
                records
            ]

        result: list[
            list[_OrderedParagraph]
        ] = []

        active: list[
            _OrderedParagraph
        ] = []

        previous_value: int | None = None
        previous_indent: float | None = None

        indents = [
            cls._paragraph_indent(
                record.paragraph
            )
            for record in records
        ]

        reference_indent = min(
            indents
        )

        indent_tolerance = (
            cls.MINIMUM_INDENT_CLUSTER_TOLERANCE
        )

        for record in records:
            paragraph = record.paragraph

            current_indent = (
                cls._paragraph_indent(
                    paragraph
                )
            )

            current_value = (
                cls._simple_numeric_value(
                    paragraph.list_marker
                )
            )

            is_top_level = (
                abs(
                    current_indent
                    - reference_indent
                )
                <= indent_tolerance
            )

            previous_was_top_level = (
                previous_indent is not None
                and abs(
                    previous_indent
                    - reference_indent
                )
                <= indent_tolerance
            )

            is_clear_restart = (
                bool(active)
                and is_top_level
                and previous_was_top_level
                and current_value == 1
                and previous_value is not None
                and previous_value >= 1
            )

            if is_clear_restart:
                result.append(
                    active
                )

                active = []

            active.append(
                record
            )

            if is_top_level:
                previous_value = (
                    current_value
                )

                previous_indent = (
                    current_indent
                )

        if active:
            result.append(
                active
            )

        return result

    # ---------------------------------------------------------
    # Sequence construction
    # ---------------------------------------------------------

    @classmethod
    def _build_sequence(
        cls,
        page: Page,
        records: list[
            _OrderedParagraph
        ],
        sequence_id: int,
    ) -> ListSequence:
        first_paragraph = (
            records[0].paragraph
        )

        container = (
            cls._resolve_container(
                page=page,
                paragraph=first_paragraph,
            )
        )

        indents = [
            cls._paragraph_indent(
                record.paragraph
            )
            for record in records
        ]

        indent_tolerance = max(
            cls.MINIMUM_INDENT_CLUSTER_TOLERANCE,
            container.width
            * cls
            .INDENT_CLUSTER_CONTAINER_RATIO,
        )

        indent_clusters = (
            cls._build_indent_clusters(
                indents=indents,
                tolerance=indent_tolerance,
            )
        )

        confidences = [
            float(
                getattr(
                    record.paragraph,
                    "list_confidence",
                    0.0,
                )
            )
            for record in records
        ]

        sequence = ListSequence(
            sequence_id=sequence_id,
            page_number=page.number,
            list_type=(
                first_paragraph.list_type
            ),
            container_type=(
                container.container_type
            ),
            container_id=(
                container.container_id
            ),
            container_left=(
                container.left
            ),
            container_right=(
                container.right
            ),
        )

        if confidences:
            sequence.set_confidence(
                fmean(
                    confidences
                )
            )

        start_value = (
            cls._simple_numeric_value(
                first_paragraph.list_marker
            )
        )

        if start_value is not None:
            sequence.start_at = max(
                start_value,
                1,
            )

        for item_index, record in enumerate(
            records
        ):
            paragraph = record.paragraph

            indent = (
                cls._paragraph_indent(
                    paragraph
                )
            )

            geometric_level = (
                cls._nearest_cluster_index(
                    value=indent,
                    clusters=indent_clusters,
                )
            )

            explicit_level = (
                cls._explicit_marker_level(
                    paragraph
                )
            )

            level = min(
                max(
                    geometric_level,
                    explicit_level,
                    0,
                ),
                cls.MAXIMUM_WORD_LIST_LEVEL,
            )

            paragraph.list_sequence_id = (
                sequence_id
            )

            paragraph.list_item_index = (
                item_index
            )

            paragraph.list_level = level

            numeric_value = (
                cls._simple_numeric_value(
                    paragraph.list_marker
                )
            )

            multilevel_value = (
                cls._multilevel_numeric_value(
                    paragraph.list_marker
                )
            )

            item = ListSequenceItem(
                page_number=page.number,
                paragraph_region_number=(
                    record.paragraph_number
                ),
                item_index=item_index,
                level=level,
                marker=str(
                    paragraph.list_marker
                    or ""
                ),
                marker_kind=getattr(
                    paragraph,
                    "list_marker_kind",
                    ListMarkerKind.UNKNOWN,
                ),
                marker_source=getattr(
                    paragraph,
                    "list_marker_source",
                    ListMarkerSource.UNKNOWN,
                ),
                indent=indent,
                numeric_value=numeric_value,
                multilevel_value=(
                    multilevel_value
                ),
            )

            sequence.items.append(
                item
            )

            sequence.maximum_level = max(
                sequence.maximum_level,
                level,
            )

        sequence.add_reason(
            (
                "Consecutive list items were grouped using "
                "reading order, container membership and "
                "vertical spacing."
            )
        )

        if sequence.maximum_level > 0:
            sequence.add_reason(
                (
                    "Nested levels were inferred from "
                    "container-relative text indentation."
                )
            )

        if len(indent_clusters) > 9:
            sequence.add_warning(
                (
                    "More than nine indentation levels were "
                    "detected; Word list levels were capped "
                    "at level 8."
                )
            )

        return sequence

    # ---------------------------------------------------------
    # Paragraph ordering
    # ---------------------------------------------------------

    @classmethod
    def _collect_ordered_paragraphs(
        cls,
        page: Page,
    ) -> list[_OrderedParagraph]:
        paragraphs_by_number: dict[
            int,
            Any,
        ] = {}

        original_order: dict[
            int,
            int,
        ] = {}

        used_numbers: set[int] = set()

        for index, paragraph in enumerate(
            page.paragraph_regions
        ):
            if getattr(
                paragraph,
                "is_list_marker_only",
                False,
            ):
                continue
    
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            raw_number = getattr(
                paragraph,
                "region_number",
                index + 1,
            )

            try:
                paragraph_number = int(
                    raw_number
                )

            except (
                TypeError,
                ValueError,
            ):
                paragraph_number = (
                    index + 1
                )

            while paragraph_number in used_numbers:
                paragraph_number += 1

            used_numbers.add(
                paragraph_number
            )

            paragraphs_by_number[
                paragraph_number
            ] = paragraph

            original_order[
                paragraph_number
            ] = index

        reading_order_by_number = {
            entry.paragraph_region_number: (
                int(
                    entry.order
                )
            )
            for entry in getattr(
                page,
                "reading_order_entries",
                [],
            )
            or []
        }

        records: list[
            _OrderedParagraph
        ] = []

        for paragraph_number, paragraph in (
            paragraphs_by_number.items()
        ):
            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    paragraph
                )
            )

            if bbox is None:
                top = float(
                    original_order[
                        paragraph_number
                    ]
                )

                left = 0.0

            else:
                left = float(
                    bbox[0]
                )

                top = float(
                    bbox[1]
                )

            order = (
                reading_order_by_number.get(
                    paragraph_number,
                    1_000_000
                    + original_order[
                        paragraph_number
                    ],
                )
            )

            records.append(
                _OrderedParagraph(
                    paragraph=paragraph,
                    paragraph_number=(
                        paragraph_number
                    ),
                    order=order,
                    top=top,
                    left=left,
                )
            )

        records.sort(
            key=lambda record: (
                record.order,
                record.top,
                record.left,
            )
        )

        return records

    # ---------------------------------------------------------
    # Container resolution
    # ---------------------------------------------------------

    @classmethod
    def _resolve_container(
        cls,
        page: Page,
        paragraph: Any,
    ) -> _ContainerReference:
        columns = list(
            getattr(
                page,
                "column_regions",
                [],
            )
            or []
        )

        explicit_column_id = getattr(
            paragraph,
            "column_id",
            None,
        )

        if len(columns) >= 2:
            for column in columns:
                if (
                    column.column_id
                    == explicit_column_id
                ):
                    bbox = (
                        RectangleUnion
                        .normalize_rectangle(
                            column.bbox
                        )
                    )

                    if bbox is not None:
                        return _ContainerReference(
                            container_type=(
                                ListContainerType
                                .COLUMN
                            ),
                            container_id=(
                                column.column_id
                            ),
                            left=float(
                                bbox[0]
                            ),
                            right=float(
                                bbox[2]
                            ),
                        )

        layout_regions = list(
            getattr(
                page,
                "layout_regions",
                [],
            )
            or []
        )

        explicit_layout_region_id = getattr(
            paragraph,
            "layout_region_id",
            None,
        )

        for region in layout_regions:
            if (
                region.region_id
                != explicit_layout_region_id
            ):
                continue

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    region.bbox
                )
            )

            if bbox is None:
                continue

            if (
                region.region_type
                == LayoutRegionType.PAGE_BODY
            ):
                container_type = (
                    ListContainerType
                    .PAGE_BODY
                )

            else:
                container_type = (
                    ListContainerType
                    .LAYOUT_REGION
                )

            return _ContainerReference(
                container_type=(
                    container_type
                ),
                container_id=(
                    region.region_id
                ),
                left=float(
                    bbox[0]
                ),
                right=float(
                    bbox[2]
                ),
            )

        for region in layout_regions:
            if (
                region.region_type
                != LayoutRegionType.PAGE_BODY
            ):
                continue

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    region.bbox
                )
            )

            if bbox is not None:
                return _ContainerReference(
                    container_type=(
                        ListContainerType
                        .PAGE_BODY
                    ),
                    container_id=(
                        region.region_id
                    ),
                    left=float(
                        bbox[0]
                    ),
                    right=float(
                        bbox[2]
                    ),
                )

        page_bbox = (
            RectangleUnion
            .normalize_rectangle(
                page.bbox
            )
        )

        if page_bbox is None:
            left = float(
                getattr(
                    paragraph,
                    "left",
                    0.0,
                )
            )

            right = float(
                getattr(
                    paragraph,
                    "right",
                    left + 1.0,
                )
            )

        else:
            left = float(
                page_bbox[0]
            )

            right = float(
                page_bbox[2]
            )

        return _ContainerReference(
            container_type=(
                ListContainerType.PAGE
            ),
            container_id=None,
            left=left,
            right=right,
        )

    # ---------------------------------------------------------
    # Indentation
    # ---------------------------------------------------------

    @staticmethod
    def _paragraph_indent(
        paragraph: Any,
    ) -> float:
        content_left = getattr(
            paragraph,
            "content_left",
            None,
        )

        if content_left is not None:
            try:
                return float(
                    content_left
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        return float(
            getattr(
                paragraph,
                "left",
                0.0,
            )
        )

    @staticmethod
    def _build_indent_clusters(
        indents: list[float],
        tolerance: float,
    ) -> list[float]:
        if not indents:
            return [
                0.0
            ]

        sorted_values = sorted(
            float(
                value
            )
            for value in indents
        )

        clusters: list[
            list[float]
        ] = []

        for value in sorted_values:
            if not clusters:
                clusters.append(
                    [value]
                )
                continue

            cluster_center = median(
                clusters[-1]
            )

            if (
                abs(
                    value
                    - cluster_center
                )
                <= tolerance
            ):
                clusters[-1].append(
                    value
                )

            else:
                clusters.append(
                    [value]
                )

        return [
            float(
                median(
                    cluster
                )
            )
            for cluster in clusters
        ]

    @staticmethod
    def _nearest_cluster_index(
        value: float,
        clusters: list[float],
    ) -> int:
        if not clusters:
            return 0

        return min(
            range(
                len(clusters)
            ),
            key=lambda index: abs(
                clusters[index]
                - value
            ),
        )

    @classmethod
    def _explicit_marker_level(
        cls,
        paragraph: Any,
    ) -> int:
        marker_kind = getattr(
            paragraph,
            "list_marker_kind",
            ListMarkerKind.UNKNOWN,
        )

        if (
            marker_kind
            != ListMarkerKind
            .MULTILEVEL_DECIMAL
        ):
            return 0

        value = (
            cls._normalized_marker_value(
                paragraph.list_marker
            )
        )

        if not value:
            return 0

        return min(
            max(
                len(
                    value.split(".")
                )
                - 1,
                0,
            ),
            cls.MAXIMUM_WORD_LIST_LEVEL,
        )

    # ---------------------------------------------------------
    # Marker values
    # ---------------------------------------------------------

    @classmethod
    def _simple_numeric_value(
        cls,
        marker: str | None,
    ) -> int | None:
        value = (
            cls._normalized_marker_value(
                marker
            )
        )

        if not value:
            return None

        if cls.DECIMAL_VALUE_PATTERN.fullmatch(
            value
        ):
            return int(
                value
            )

        if (
            len(value) == 1
            and value.isalpha()
        ):
            return (
                ord(
                    value.lower()
                )
                - ord("a")
                + 1
            )

        if cls.ROMAN_VALUE_PATTERN.fullmatch(
            value
        ):
            return cls._roman_to_integer(
                value
            )

        return None

    @classmethod
    def _multilevel_numeric_value(
        cls,
        marker: str | None,
    ) -> tuple[int, ...] | None:
        value = (
            cls._normalized_marker_value(
                marker
            )
        )

        if not value:
            return None

        if not cls.MULTILEVEL_VALUE_PATTERN.fullmatch(
            value
        ):
            return None

        return tuple(
            int(
                part
            )
            for part in value.split(".")
        )

    @staticmethod
    def _normalized_marker_value(
        marker: str | None,
    ) -> str:
        if not marker:
            return ""

        value = str(
            marker
        ).strip()

        if (
            value.startswith("(")
            and value.endswith(")")
        ):
            value = value[
                1:-1
            ].strip()

        else:
            value = value.rstrip(
                ".)"
            ).strip()

        return value

    @staticmethod
    def _roman_to_integer(
        value: str,
    ) -> int | None:
        roman_values = {
            "i": 1,
            "v": 5,
            "x": 10,
            "l": 50,
            "c": 100,
            "d": 500,
            "m": 1000,
        }

        total = 0
        previous = 0

        for character in reversed(
            value.lower()
        ):
            current = roman_values.get(
                character
            )

            if current is None:
                return None

            if current < previous:
                total -= current

            else:
                total += current
                previous = current

        return total or None

    # ---------------------------------------------------------
    # Other helpers
    # ---------------------------------------------------------

    @classmethod
    def _is_list_item(
        cls,
        paragraph: Any,
    ) -> bool:
        if (
            getattr(
                paragraph,
                "list_type",
                None,
            )
            not in {
                "bullet",
                "number",
            }
        ):
            return False

        try:
            confidence = float(
                getattr(
                    paragraph,
                    "list_confidence",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        return (
            confidence
            >= cls.MINIMUM_LIST_CONFIDENCE
        )

    @staticmethod
    def _estimate_line_height(
        paragraph: Any,
    ) -> float:
        heights: list[float] = []

        for line in getattr(
            paragraph,
            "lines",
            [],
        ) or []:
            for span in getattr(
                line,
                "spans",
                [],
            ) or []:
                try:
                    height = (
                        float(
                            span.bottom
                        )
                        - float(
                            span.top
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                    AttributeError,
                ):
                    continue

                if height > 0.0:
                    heights.append(
                        height
                    )

        if heights:
            return float(
                median(
                    heights
                )
            )

        try:
            return max(
                float(
                    paragraph.bottom
                )
                - float(
                    paragraph.top
                ),
                1.0,
            )

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return 12.0