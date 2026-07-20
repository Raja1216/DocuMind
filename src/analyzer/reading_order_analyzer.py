from __future__ import annotations

import unicodedata

from dataclasses import dataclass
from typing import Any, Iterable

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
from src.models.page import Page
from src.models.reading_order import (
    ReadingDirection,
    ReadingOrderEntry,
    ReadingOrderRole,
)
from src.utils.rectangle_union import (
    Bounds,
    RectangleUnion,
)


@dataclass(slots=True)
class _ParagraphNode:
    """
    Internal normalized paragraph representation.
    """

    number: int

    paragraph: Any

    text: str

    bbox: Bounds

    @property
    def left(self) -> float:
        return self.bbox[0]

    @property
    def top(self) -> float:
        return self.bbox[1]

    @property
    def right(self) -> float:
        return self.bbox[2]

    @property
    def bottom(self) -> float:
        return self.bbox[3]

    @property
    def center_x(self) -> float:
        return (
            self.left + self.right
        ) / 2.0

    @property
    def center_y(self) -> float:
        return (
            self.top + self.bottom
        ) / 2.0


@dataclass(slots=True)
class _ResolvedNode:
    """
    Paragraph with its resolved semantic container.
    """

    node: _ParagraphNode

    role: ReadingOrderRole

    layout_region_id: int | None

    column_id: int | None


class ReadingOrderAnalyzer:
    """
    Assigns stable reading order to page paragraphs.

    Current ordering strategy:

        1. Header
        2. Page-body content
        3. Spanning paragraphs and column sections
        4. Unassigned content
        5. Footer

    This analyzer does not change paragraph text or DOCX
    rendering.
    """

    SPANNING_VERTICAL_TOLERANCE = 2.0

    MINIMUM_DIRECTION_CHARACTERS = 3

    RTL_BIDI_CLASSES = {
        "R",
        "AL",
        "RLE",
        "RLO",
        "RLI",
        "AN",
    }

    LTR_BIDI_CLASSES = {
        "L",
        "LRE",
        "LRO",
        "LRI",
    }

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> None:
        """
        Resolve reading order for every page.
        """

        for page in document.pages:
            cls.analyze_page(
                page
            )

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> list[ReadingOrderEntry]:
        """
        Resolve reading order for one page.

        Reanalysis replaces all old entries and metadata.
        """

        page.reading_order_entries.clear()

        nodes = cls._collect_paragraph_nodes(
            page
        )

        for node in nodes:
            cls._reset_paragraph_metadata(
                node.paragraph
            )

        page.reading_direction = (
            cls._detect_reading_direction(
                nodes
            )
        )

        if not nodes:
            cls._reset_region_reading_orders(
                page
            )

            return page.reading_order_entries

        nodes_by_number = {
            node.number: node
            for node in nodes
        }

        header_region = (
            cls._first_layout_region(
                page=page,
                region_type=(
                    LayoutRegionType.HEADER
                ),
            )
        )

        body_region = (
            cls._first_layout_region(
                page=page,
                region_type=(
                    LayoutRegionType.PAGE_BODY
                ),
            )
        )

        footer_region = (
            cls._first_layout_region(
                page=page,
                region_type=(
                    LayoutRegionType.FOOTER
                ),
            )
        )

        resolved_nodes: list[
            _ResolvedNode
        ] = []

        consumed_numbers: set[int] = set()

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        if header_region is not None:
            header_nodes = (
                cls._nodes_for_region(
                    region=header_region,
                    nodes_by_number=(
                        nodes_by_number
                    ),
                )
            )

            for node in cls._sort_row_major(
                nodes=header_nodes,
                direction=(
                    page.reading_direction
                ),
            ):
                resolved_nodes.append(
                    _ResolvedNode(
                        node=node,
                        role=(
                            ReadingOrderRole.HEADER
                        ),
                        layout_region_id=(
                            header_region.region_id
                        ),
                        column_id=None,
                    )
                )

                consumed_numbers.add(
                    node.number
                )

        # -----------------------------------------------------
        # Page body
        # -----------------------------------------------------

        if body_region is not None:
            body_resolved_nodes = (
                cls._resolve_body_order(
                    page=page,
                    body_region=body_region,
                    nodes_by_number=(
                        nodes_by_number
                    ),
                )
            )

            for resolved_node in body_resolved_nodes:
                if (
                    resolved_node.node.number
                    in consumed_numbers
                ):
                    continue

                resolved_nodes.append(
                    resolved_node
                )

                consumed_numbers.add(
                    resolved_node.node.number
                )

        # -----------------------------------------------------
        # Unassigned paragraphs
        #
        # Never silently lose content because one paragraph
        # was not attached to a layout region.
        # -----------------------------------------------------

        footer_numbers = set()

        if footer_region is not None:
            footer_numbers = set(
                footer_region
                .paragraph_region_numbers
            )

        unassigned_nodes = [
            node
            for node in nodes
            if (
                node.number
                not in consumed_numbers
                and node.number
                not in footer_numbers
            )
        ]

        for node in cls._sort_row_major(
            nodes=unassigned_nodes,
            direction=(
                page.reading_direction
            ),
        ):
            resolved_nodes.append(
                _ResolvedNode(
                    node=node,
                    role=(
                        ReadingOrderRole.UNASSIGNED
                    ),
                    layout_region_id=None,
                    column_id=None,
                )
            )

            consumed_numbers.add(
                node.number
            )

        # -----------------------------------------------------
        # Footer
        # -----------------------------------------------------

        if footer_region is not None:
            footer_nodes = (
                cls._nodes_for_region(
                    region=footer_region,
                    nodes_by_number=(
                        nodes_by_number
                    ),
                )
            )

            for node in cls._sort_row_major(
                nodes=footer_nodes,
                direction=(
                    page.reading_direction
                ),
            ):
                if node.number in consumed_numbers:
                    continue

                resolved_nodes.append(
                    _ResolvedNode(
                        node=node,
                        role=(
                            ReadingOrderRole.FOOTER
                        ),
                        layout_region_id=(
                            footer_region.region_id
                        ),
                        column_id=None,
                    )
                )

                consumed_numbers.add(
                    node.number
                )

        cls._create_entries(
            page=page,
            resolved_nodes=resolved_nodes,
        )

        cls._assign_layout_region_orders(
            page
        )

        return page.reading_order_entries

    # ---------------------------------------------------------
    # Body ordering
    # ---------------------------------------------------------

    @classmethod
    def _resolve_body_order(
        cls,
        page: Page,
        body_region: LayoutRegion,
        nodes_by_number: dict[
            int,
            _ParagraphNode,
        ],
    ) -> list[_ResolvedNode]:
        body_nodes = cls._nodes_for_region(
            region=body_region,
            nodes_by_number=nodes_by_number,
        )

        if not body_nodes:
            return []

        columns = list(
            page.column_regions
        )

        if not columns:
            return [
                _ResolvedNode(
                    node=node,
                    role=ReadingOrderRole.BODY,
                    layout_region_id=(
                        body_region.region_id
                    ),
                    column_id=None,
                )
                for node in cls._sort_row_major(
                    nodes=body_nodes,
                    direction=(
                        page.reading_direction
                    ),
                )
            ]

        ordered_columns = (
            cls._columns_in_reading_order(
                columns=columns,
                direction=(
                    page.reading_direction
                ),
            )
        )

        for order_index, column in enumerate(
            ordered_columns,
            start=1,
        ):
            column.reading_order = (
                order_index
            )

        column_layout_region_ids = (
            cls._match_column_layout_regions(
                page=page,
                columns=columns,
            )
        )

        column_nodes: dict[
            int,
            list[_ParagraphNode],
        ] = {}

        all_column_paragraph_numbers: set[
            int
        ] = set()

        for column in ordered_columns:
            nodes = [
                nodes_by_number[
                    paragraph_number
                ]
                for paragraph_number
                in column.paragraph_region_numbers
                if paragraph_number
                in nodes_by_number
            ]

            column_nodes[
                column.column_id
            ] = cls._sort_column_nodes(
                nodes=nodes,
                direction=(
                    page.reading_direction
                ),
            )

            all_column_paragraph_numbers.update(
                node.number
                for node in nodes
            )

        spanning_nodes = [
            node
            for node in body_nodes
            if (
                node.number
                not in all_column_paragraph_numbers
            )
        ]

        spanning_nodes = cls._sort_row_major(
            nodes=spanning_nodes,
            direction=(
                page.reading_direction
            ),
        )

        consumed_column_numbers: set[int] = (
            set()
        )

        resolved_nodes: list[
            _ResolvedNode
        ] = []

        # A spanning paragraph divides the columns into
        # vertical reading sections:
        #
        #   heading
        #   left column then right column
        #   spanning subheading
        #   left column then right column
        for spanning_node in spanning_nodes:
            before_spanning = (
                cls._resolve_column_segment(
                    ordered_columns=(
                        ordered_columns
                    ),
                    column_nodes=column_nodes,
                    column_layout_region_ids=(
                        column_layout_region_ids
                    ),
                    consumed_numbers=(
                        consumed_column_numbers
                    ),
                    maximum_center_y=(
                        spanning_node.center_y
                    ),
                )
            )

            resolved_nodes.extend(
                before_spanning
            )

            resolved_nodes.append(
                _ResolvedNode(
                    node=spanning_node,
                    role=(
                        ReadingOrderRole
                        .BODY_SPANNING
                    ),
                    layout_region_id=(
                        body_region.region_id
                    ),
                    column_id=None,
                )
            )

        remaining_columns = (
            cls._resolve_column_segment(
                ordered_columns=ordered_columns,
                column_nodes=column_nodes,
                column_layout_region_ids=(
                    column_layout_region_ids
                ),
                consumed_numbers=(
                    consumed_column_numbers
                ),
                maximum_center_y=None,
            )
        )

        resolved_nodes.extend(
            remaining_columns
        )

        return resolved_nodes

    @classmethod
    def _resolve_column_segment(
        cls,
        ordered_columns: list[
            ColumnRegion
        ],
        column_nodes: dict[
            int,
            list[_ParagraphNode],
        ],
        column_layout_region_ids: dict[
            int,
            int | None,
        ],
        consumed_numbers: set[int],
        maximum_center_y: float | None,
    ) -> list[_ResolvedNode]:
        resolved_nodes: list[
            _ResolvedNode
        ] = []

        for column in ordered_columns:
            for node in column_nodes.get(
                column.column_id,
                [],
            ):
                if node.number in consumed_numbers:
                    continue

                if (
                    maximum_center_y is not None
                    and node.center_y
                    >= (
                        maximum_center_y
                        - cls
                        .SPANNING_VERTICAL_TOLERANCE
                    )
                ):
                    continue

                resolved_nodes.append(
                    _ResolvedNode(
                        node=node,
                        role=(
                            ReadingOrderRole.COLUMN
                        ),
                        layout_region_id=(
                            column_layout_region_ids.get(
                                column.column_id
                            )
                        ),
                        column_id=(
                            column.column_id
                        ),
                    )
                )

                consumed_numbers.add(
                    node.number
                )

        return resolved_nodes

    # ---------------------------------------------------------
    # Entry creation
    # ---------------------------------------------------------

    @classmethod
    def _create_entries(
        cls,
        page: Page,
        resolved_nodes: list[
            _ResolvedNode
        ],
    ) -> None:
        for order, resolved_node in enumerate(
            resolved_nodes,
            start=1,
        ):
            node = resolved_node.node

            entry = ReadingOrderEntry(
                order=order,
                page_number=page.number,
                paragraph_region_number=(
                    node.number
                ),
                role=resolved_node.role,
                bbox=cls._make_rectangle(
                    node.bbox
                ),
                layout_region_id=(
                    resolved_node
                    .layout_region_id
                ),
                column_id=(
                    resolved_node.column_id
                ),
            )

            page.reading_order_entries.append(
                entry
            )

            setattr(
                node.paragraph,
                "reading_order",
                order,
            )

            setattr(
                node.paragraph,
                "layout_region_id",
                resolved_node.layout_region_id,
            )

            setattr(
                node.paragraph,
                "column_id",
                resolved_node.column_id,
            )

    @classmethod
    def _assign_layout_region_orders(
        cls,
        page: Page,
    ) -> None:
        """
        Store the first paragraph order of each layout region.
        """

        entry_orders = {
            entry.paragraph_region_number: (
                entry.order
            )
            for entry in page.reading_order_entries
        }

        for region in page.layout_regions:
            paragraph_orders = [
                entry_orders[
                    paragraph_number
                ]
                for paragraph_number
                in region.paragraph_region_numbers
                if paragraph_number
                in entry_orders
            ]

            region.reading_order = (
                min(paragraph_orders)
                if paragraph_orders
                else None
            )

    # ---------------------------------------------------------
    # Direction detection
    # ---------------------------------------------------------

    @classmethod
    def _detect_reading_direction(
        cls,
        nodes: Iterable[_ParagraphNode],
    ) -> ReadingDirection:
        rtl_count = 0
        ltr_count = 0

        for node in nodes:
            for character in node.text:
                bidi_class = (
                    unicodedata.bidirectional(
                        character
                    )
                )

                if (
                    bidi_class
                    in cls.RTL_BIDI_CLASSES
                ):
                    rtl_count += 1

                elif (
                    bidi_class
                    in cls.LTR_BIDI_CLASSES
                ):
                    ltr_count += 1

        directional_count = (
            rtl_count + ltr_count
        )

        if (
            directional_count
            < cls.MINIMUM_DIRECTION_CHARACTERS
        ):
            return (
                ReadingDirection
                .LEFT_TO_RIGHT
            )

        if rtl_count > ltr_count:
            return (
                ReadingDirection
                .RIGHT_TO_LEFT
            )

        return (
            ReadingDirection
            .LEFT_TO_RIGHT
        )

    # ---------------------------------------------------------
    # Paragraph collection
    # ---------------------------------------------------------

    @classmethod
    def _collect_paragraph_nodes(
        cls,
        page: Page,
    ) -> list[_ParagraphNode]:
        nodes: list[_ParagraphNode] = []

        used_numbers: set[int] = set()

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    paragraph
                )
            )

            if bbox is None:
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
                paragraph_number = index + 1

            # Region numbers should be unique. If malformed
            # input contains duplicates, use a stable fallback.
            while paragraph_number in used_numbers:
                paragraph_number += 1

            used_numbers.add(
                paragraph_number
            )

            nodes.append(
                _ParagraphNode(
                    number=paragraph_number,
                    paragraph=paragraph,
                    text=text,
                    bbox=bbox,
                )
            )

        return nodes

    @staticmethod
    def _reset_paragraph_metadata(
        paragraph: Any,
    ) -> None:
        setattr(
            paragraph,
            "reading_order",
            None,
        )

        setattr(
            paragraph,
            "layout_region_id",
            None,
        )

        setattr(
            paragraph,
            "column_id",
            None,
        )

    @staticmethod
    def _reset_region_reading_orders(
        page: Page,
    ) -> None:
        for region in page.layout_regions:
            region.reading_order = None

        for column in page.column_regions:
            column.reading_order = None

    # ---------------------------------------------------------
    # Region matching
    # ---------------------------------------------------------

    @staticmethod
    def _first_layout_region(
        page: Page,
        region_type: LayoutRegionType,
    ) -> LayoutRegion | None:
        return next(
            (
                region
                for region
                in page.layout_regions
                if (
                    region.region_type
                    == region_type
                )
            ),
            None,
        )

    @staticmethod
    def _nodes_for_region(
        region: LayoutRegion,
        nodes_by_number: dict[
            int,
            _ParagraphNode,
        ],
    ) -> list[_ParagraphNode]:
        return [
            nodes_by_number[
                paragraph_number
            ]
            for paragraph_number
            in region.paragraph_region_numbers
            if paragraph_number
            in nodes_by_number
        ]

    @classmethod
    def _match_column_layout_regions(
        cls,
        page: Page,
        columns: list[ColumnRegion],
    ) -> dict[int, int | None]:
        """
        Match ColumnRegion objects to LayoutRegionType.COLUMN
        containers by horizontal position.
        """

        layout_columns = sorted(
            [
                region
                for region
                in page.layout_regions
                if (
                    region.region_type
                    == LayoutRegionType.COLUMN
                )
            ],
            key=lambda region: (
                region.left,
                region.top,
            ),
        )

        sorted_columns = sorted(
            columns,
            key=lambda column: (
                column.left,
                column.top,
            ),
        )

        result: dict[
            int,
            int | None,
        ] = {
            column.column_id: None
            for column in columns
        }

        for column, layout_region in zip(
            sorted_columns,
            layout_columns,
        ):
            result[
                column.column_id
            ] = layout_region.region_id

        return result

    # ---------------------------------------------------------
    # Sorting helpers
    # ---------------------------------------------------------

    @staticmethod
    def _columns_in_reading_order(
        columns: list[ColumnRegion],
        direction: ReadingDirection,
    ) -> list[ColumnRegion]:
        reverse_horizontal_order = (
            direction
            == ReadingDirection.RIGHT_TO_LEFT
        )

        return sorted(
            columns,
            key=lambda column: (
                column.center_x,
                column.top,
            ),
            reverse=(
                reverse_horizontal_order
            ),
        )

    @staticmethod
    def _sort_column_nodes(
        nodes: Iterable[_ParagraphNode],
        direction: ReadingDirection,
    ) -> list[_ParagraphNode]:
        horizontal_multiplier = (
            -1.0
            if (
                direction
                == ReadingDirection.RIGHT_TO_LEFT
            )
            else 1.0
        )

        return sorted(
            nodes,
            key=lambda node: (
                node.top,
                node.left
                * horizontal_multiplier,
                node.bottom,
            ),
        )

    @staticmethod
    def _sort_row_major(
        nodes: Iterable[_ParagraphNode],
        direction: ReadingDirection,
    ) -> list[_ParagraphNode]:
        horizontal_multiplier = (
            -1.0
            if (
                direction
                == ReadingDirection.RIGHT_TO_LEFT
            )
            else 1.0
        )

        return sorted(
            nodes,
            key=lambda node: (
                node.top,
                node.left
                * horizontal_multiplier,
                node.bottom,
            ),
        )

    @staticmethod
    def _make_rectangle(
        bounds: Bounds,
    ) -> Rectangle:
        return Rectangle(
            left=float(
                bounds[0]
            ),
            top=float(
                bounds[1]
            ),
            right=float(
                bounds[2]
            ),
            bottom=float(
                bounds[3]
            ),
        )