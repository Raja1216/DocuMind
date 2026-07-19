from __future__ import annotations

import re
import unicodedata

from collections import defaultdict
from dataclasses import dataclass
from math import ceil
from statistics import median
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
from src.utils.rectangle_union import (
    Bounds,
    RectangleUnion,
)


@dataclass(slots=True)
class _ParagraphItem:
    """
    Normalized paragraph geometry used internally by the
    layout analyzer.
    """

    number: int
    paragraph: Any
    bbox: Bounds
    text: str

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
    def width(self) -> float:
        return max(
            self.right - self.left,
            0.0,
        )

    @property
    def height(self) -> float:
        return max(
            self.bottom - self.top,
            0.0,
        )

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
class _BandCandidate:
    """
    Possible repeated header or footer paragraph.
    """

    page_number: int
    paragraph_number: int

    band: str
    signature: str

    horizontal_bucket: int
    relative_center_y: float

    bbox: Bounds


class LayoutRegionAnalyzer:
    """
    Detects page-level layout containers.

    Current responsibilities:

        repeated headers;
        repeated footers;
        sequential page-number footers;
        page-body region;
        strong paragraph columns.

    This analyzer does not determine final reading order or
    paragraph alignment.
    """

    # ---------------------------------------------------------
    # Header/footer configuration
    # ---------------------------------------------------------

    HEADER_FOOTER_BAND_RATIO = 0.14

    MINIMUM_BAND_HEIGHT = 48.0
    MAXIMUM_BAND_HEIGHT = 110.0

    MAXIMUM_BAND_TEXT_LENGTH = 180

    MINIMUM_REPEAT_RATIO = 0.50

    MAXIMUM_RELATIVE_POSITION_SPREAD = 0.035

    HORIZONTAL_BUCKET_SIZE = 0.08

    # ---------------------------------------------------------
    # Column configuration
    # ---------------------------------------------------------

    MINIMUM_COLUMN_TEXT_LENGTH = 20

    MINIMUM_COLUMN_PARAGRAPHS = 2

    MINIMUM_COLUMN_CANDIDATES = 4

    MAXIMUM_COLUMN_COUNT = 4

    MINIMUM_PARAGRAPH_WIDTH_RATIO = 0.10

    MAXIMUM_COLUMN_PARAGRAPH_WIDTH_RATIO = 0.78

    SPANNING_PARAGRAPH_WIDTH_RATIO = 0.82

    LEFT_EDGE_CLUSTER_TOLERANCE_RATIO = 0.045

    MINIMUM_LEFT_EDGE_CLUSTER_TOLERANCE = 10.0

    MERGE_CLUSTER_DISTANCE_RATIO = 0.10

    MINIMUM_COLUMN_LEFT_SEPARATION_RATIO = 0.18

    MINIMUM_GUTTER_RATIO = 0.025

    MINIMUM_GUTTER_POINTS = 12.0

    MINIMUM_COLUMN_VERTICAL_OVERLAP = 0.25

    COLUMN_BOUNDARY_TOLERANCE = 2.0

    # ---------------------------------------------------------
    # General geometry
    # ---------------------------------------------------------

    REGION_PADDING = 3.0

    BODY_PADDING_RATIO = 0.01

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> None:
        """
        Detect layout regions for every document page.

        Header/footer repetition must be analyzed at document
        level because it requires comparing multiple pages.
        """

        pages = list(
            document.pages
        )

        paragraph_items_by_page: dict[
            int,
            list[_ParagraphItem],
        ] = {}

        for page in pages:
            # Reanalysis must never preserve stale regions.
            page.layout_regions.clear()
            page.column_regions.clear()

            paragraph_items_by_page[
                page.number
            ] = cls._collect_paragraph_items(
                page
            )

        repeated_band_matches = (
            cls._detect_repeated_bands(
                pages=pages,
                paragraph_items_by_page=(
                    paragraph_items_by_page
                ),
            )
        )

        for page in pages:
            cls._build_page_regions(
                page=page,
                paragraph_items=(
                    paragraph_items_by_page[
                        page.number
                    ]
                ),
                band_matches=(
                    repeated_band_matches.get(
                        page.number,
                        {
                            "header": {},
                            "footer": {},
                        },
                    )
                ),
            )

    # ---------------------------------------------------------
    # Paragraph preparation
    # ---------------------------------------------------------

    @classmethod
    def _collect_paragraph_items(
        cls,
        page: Page,
    ) -> list[_ParagraphItem]:
        items: list[_ParagraphItem] = []

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

            raw_region_number = getattr(
                paragraph,
                "region_number",
                index + 1,
            )

            try:
                region_number = int(
                    raw_region_number
                )

            except (
                TypeError,
                ValueError,
            ):
                region_number = index + 1

            items.append(
                _ParagraphItem(
                    number=region_number,
                    paragraph=paragraph,
                    bbox=bbox,
                    text=text,
                )
            )

        return items

    # ---------------------------------------------------------
    # Header/footer detection
    # ---------------------------------------------------------

    @classmethod
    def _detect_repeated_bands(
        cls,
        pages: list[Page],
        paragraph_items_by_page: dict[
            int,
            list[_ParagraphItem],
        ],
    ) -> dict[
        int,
        dict[
            str,
            dict[int, float],
        ],
    ]:
        """
        Return repeated header/footer paragraph matches.

        Result format:

            {
                page_number: {
                    "header": {
                        paragraph_number: confidence
                    },
                    "footer": {
                        paragraph_number: confidence
                    }
                }
            }
        """

        matches: dict[
            int,
            dict[
                str,
                dict[int, float],
            ],
        ] = {
            page.number: {
                "header": {},
                "footer": {},
            }
            for page in pages
        }

        if len(pages) < 2:
            return matches

        candidate_groups: dict[
            tuple[str, str, int],
            list[_BandCandidate],
        ] = defaultdict(list)

        for page in pages:
            page_bounds = (
                RectangleUnion
                .normalize_rectangle(
                    page.bbox
                )
            )

            if page_bounds is None:
                continue

            page_width = max(
                page_bounds[2]
                - page_bounds[0],
                1.0,
            )

            page_height = max(
                page_bounds[3]
                - page_bounds[1],
                1.0,
            )

            band_height = min(
                max(
                    page_height
                    * cls.HEADER_FOOTER_BAND_RATIO,
                    cls.MINIMUM_BAND_HEIGHT,
                ),
                cls.MAXIMUM_BAND_HEIGHT,
            )

            header_bottom = (
                page_bounds[1]
                + band_height
            )

            footer_top = (
                page_bounds[3]
                - band_height
            )

            for item in paragraph_items_by_page.get(
                page.number,
                [],
            ):
                if (
                    len(item.text)
                    > cls.MAXIMUM_BAND_TEXT_LENGTH
                ):
                    continue

                if item.center_y <= header_bottom:
                    band = "header"

                elif item.center_y >= footer_top:
                    band = "footer"

                else:
                    continue

                signature = (
                    cls._header_footer_signature(
                        item.text
                    )
                )

                if not signature:
                    continue

                horizontal_ratio = (
                    item.center_x
                    - page_bounds[0]
                ) / page_width

                horizontal_bucket = int(
                    round(
                        horizontal_ratio
                        / cls.HORIZONTAL_BUCKET_SIZE
                    )
                )

                relative_center_y = (
                    item.center_y
                    - page_bounds[1]
                ) / page_height

                candidate = _BandCandidate(
                    page_number=page.number,
                    paragraph_number=item.number,
                    band=band,
                    signature=signature,
                    horizontal_bucket=(
                        horizontal_bucket
                    ),
                    relative_center_y=(
                        relative_center_y
                    ),
                    bbox=item.bbox,
                )

                group_key = (
                    band,
                    signature,
                    horizontal_bucket,
                )

                candidate_groups[
                    group_key
                ].append(
                    candidate
                )

        required_page_count = max(
            2,
            ceil(
                len(pages)
                * cls.MINIMUM_REPEAT_RATIO
            ),
        )

        for candidates in candidate_groups.values():
            unique_page_numbers = {
                candidate.page_number
                for candidate in candidates
            }

            if (
                len(unique_page_numbers)
                < required_page_count
            ):
                continue

            relative_positions = [
                candidate.relative_center_y
                for candidate in candidates
            ]

            position_spread = (
                max(relative_positions)
                - min(relative_positions)
            )

            if (
                position_spread
                > cls.MAXIMUM_RELATIVE_POSITION_SPREAD
            ):
                continue

            support_ratio = (
                len(unique_page_numbers)
                / len(pages)
            )

            position_score = max(
                0.0,
                1.0
                - (
                    position_spread
                    / max(
                        cls.MAXIMUM_RELATIVE_POSITION_SPREAD,
                        0.001,
                    )
                ),
            )

            confidence = (
                0.55
                + support_ratio * 0.30
                + position_score * 0.15
            )

            confidence = cls._clamp(
                confidence
            )

            for candidate in candidates:
                current_confidence = matches[
                    candidate.page_number
                ][candidate.band].get(
                    candidate.paragraph_number,
                    0.0,
                )

                matches[
                    candidate.page_number
                ][candidate.band][
                    candidate.paragraph_number
                ] = max(
                    current_confidence,
                    confidence,
                )

        return matches

    @classmethod
    def _header_footer_signature(
        cls,
        text: str,
    ) -> str:
        """
        Normalize repeated header/footer text.

        Page numbers such as:

            1
            2
            Page 3
            Page 4 of 20
            IV

        receive one common signature.
        """

        normalized = unicodedata.normalize(
            "NFKC",
            text,
        )

        normalized = " ".join(
            normalized.split()
        ).strip().lower()

        if not normalized:
            return ""

        page_number_pattern = re.compile(
            r"""
            ^
            (?:page\s*)?
            (?:
                \d+
                |
                [ivxlcdm]+
            )
            (?:
                \s*
                (?:
                    of
                    |
                    /
                )
                \s*
                (?:
                    \d+
                    |
                    [ivxlcdm]+
                )
            )?
            $
            """,
            re.IGNORECASE
            | re.VERBOSE,
        )

        if page_number_pattern.fullmatch(
            normalized
        ):
            return "__page_number__"

        # Normalize changing numbers such as dates, section
        # numbers and "Page 2 of 20".
        normalized = re.sub(
            r"\d+(?:[.,:/-]\d+)*",
            "<n>",
            normalized,
        )

        normalized = re.sub(
            r"[^\w<>]+",
            " ",
            normalized,
            flags=re.UNICODE,
        )

        normalized = " ".join(
            normalized.split()
        ).strip()

        if len(normalized) < 2:
            return ""

        return normalized

    # ---------------------------------------------------------
    # Region creation
    # ---------------------------------------------------------

    @classmethod
    def _build_page_regions(
        cls,
        page: Page,
        paragraph_items: list[_ParagraphItem],
        band_matches: dict[
            str,
            dict[int, float],
        ],
    ) -> None:
        header_numbers = set(
            band_matches.get(
                "header",
                {},
            )
        )

        footer_numbers = set(
            band_matches.get(
                "footer",
                {},
            )
        )

        header_items = [
            item
            for item in paragraph_items
            if item.number in header_numbers
        ]

        footer_items = [
            item
            for item in paragraph_items
            if item.number in footer_numbers
        ]

        body_items = [
            item
            for item in paragraph_items
            if (
                item.number
                not in header_numbers
                and item.number
                not in footer_numbers
            )
        ]

        page_bounds = (
            RectangleUnion
            .normalize_rectangle(
                page.bbox
            )
        )

        if page_bounds is None:
            return

        next_region_id = 1

        header_region: LayoutRegion | None = None
        footer_region: LayoutRegion | None = None

        if header_items:
            header_bbox = cls._items_bbox(
                items=header_items,
                clip=page_bounds,
                padding=cls.REGION_PADDING,
            )

            if header_bbox is not None:
                header_region = LayoutRegion(
                    region_id=next_region_id,
                    page_number=page.number,
                    region_type=(
                        LayoutRegionType.HEADER
                    ),
                    bbox=cls._make_rectangle(
                        header_bbox
                    ),
                )

                cls._attach_items_to_layout_region(
                    region=header_region,
                    items=header_items,
                )

                header_confidences = [
                    band_matches[
                        "header"
                    ].get(
                        item.number,
                        0.0,
                    )
                    for item in header_items
                ]

                header_region.set_confidence(
                    cls._average(
                        header_confidences
                    )
                )

                header_region.add_reason(
                    (
                        "Paragraph content and position "
                        "repeat in the upper page band."
                    )
                )

                page.layout_regions.append(
                    header_region
                )

                next_region_id += 1

        if footer_items:
            footer_bbox = cls._items_bbox(
                items=footer_items,
                clip=page_bounds,
                padding=cls.REGION_PADDING,
            )

            if footer_bbox is not None:
                footer_region = LayoutRegion(
                    region_id=next_region_id,
                    page_number=page.number,
                    region_type=(
                        LayoutRegionType.FOOTER
                    ),
                    bbox=cls._make_rectangle(
                        footer_bbox
                    ),
                )

                cls._attach_items_to_layout_region(
                    region=footer_region,
                    items=footer_items,
                )

                footer_confidences = [
                    band_matches[
                        "footer"
                    ].get(
                        item.number,
                        0.0,
                    )
                    for item in footer_items
                ]

                footer_region.set_confidence(
                    cls._average(
                        footer_confidences
                    )
                )

                footer_region.add_reason(
                    (
                        "Paragraph content and position "
                        "repeat in the lower page band."
                    )
                )

                page.layout_regions.append(
                    footer_region
                )

                next_region_id += 1

        body_bbox = cls._resolve_body_bbox(
            page_bounds=page_bounds,
            body_items=body_items,
            header_region=header_region,
            footer_region=footer_region,
        )

        body_region = LayoutRegion(
            region_id=next_region_id,
            page_number=page.number,
            region_type=(
                LayoutRegionType.PAGE_BODY
            ),
            bbox=cls._make_rectangle(
                body_bbox
            ),
        )

        body_region.set_confidence(
            0.90
            if body_items
            else 0.60
        )

        body_region.add_reason(
            (
                "Page-body bounds exclude detected "
                "header and footer regions."
            )
        )

        cls._attach_items_to_layout_region(
            region=body_region,
            items=body_items,
        )

        page.layout_regions.append(
            body_region
        )

        next_region_id += 1

        (
            column_groups,
            spanning_items,
            column_confidence,
            column_reason,
        ) = cls._detect_column_groups(
            body_items=body_items,
            body_bbox=body_bbox,
        )

        for column_index, column_items in enumerate(
            column_groups
        ):
            column_bbox = cls._items_bbox(
                items=column_items,
                clip=body_bbox,
                padding=cls.REGION_PADDING,
            )

            if column_bbox is None:
                continue

            layout_column_region = LayoutRegion(
                region_id=next_region_id,
                page_number=page.number,
                region_type=(
                    LayoutRegionType.COLUMN
                ),
                bbox=cls._make_rectangle(
                    column_bbox
                ),
                parent_region_id=(
                    body_region.region_id
                ),
            )

            layout_column_region.set_confidence(
                column_confidence
            )

            layout_column_region.add_reason(
                column_reason
            )

            cls._attach_items_to_layout_region(
                region=layout_column_region,
                items=column_items,
            )

            page.layout_regions.append(
                layout_column_region
            )

            body_region.add_child_region(
                layout_column_region.region_id
            )

            column_region = ColumnRegion(
                column_id=(
                    column_index + 1
                ),
                page_number=page.number,
                column_index=column_index,
                bbox=cls._make_rectangle(
                    column_bbox
                ),
                parent_region_id=(
                    body_region.region_id
                ),
            )

            column_region.set_confidence(
                column_confidence
            )

            column_region.add_reason(
                column_reason
            )

            cls._attach_items_to_column_region(
                region=column_region,
                items=column_items,
            )

            page.column_regions.append(
                column_region
            )

            next_region_id += 1

        if spanning_items:
            body_region.add_reason(
                (
                    f"{len(spanning_items)} full-width "
                    "or column-spanning paragraph(s) "
                    "remain assigned to the page body."
                )
            )

    @classmethod
    def _resolve_body_bbox(
        cls,
        page_bounds: Bounds,
        body_items: list[_ParagraphItem],
        header_region: LayoutRegion | None,
        footer_region: LayoutRegion | None,
    ) -> Bounds:
        page_left = page_bounds[0]
        page_top = page_bounds[1]
        page_right = page_bounds[2]
        page_bottom = page_bounds[3]

        page_width = max(
            page_right - page_left,
            1.0,
        )

        horizontal_padding = max(
            4.0,
            page_width
            * cls.BODY_PADDING_RATIO,
        )

        minimum_top = page_top
        maximum_bottom = page_bottom

        if header_region is not None:
            minimum_top = min(
                max(
                    header_region.bottom
                    + cls.REGION_PADDING,
                    page_top,
                ),
                page_bottom,
            )

        if footer_region is not None:
            maximum_bottom = max(
                min(
                    footer_region.top
                    - cls.REGION_PADDING,
                    page_bottom,
                ),
                page_top,
            )

        if body_items:
            content_left = min(
                item.left
                for item in body_items
            )

            content_top = min(
                item.top
                for item in body_items
            )

            content_right = max(
                item.right
                for item in body_items
            )

            content_bottom = max(
                item.bottom
                for item in body_items
            )

            left = max(
                page_left,
                content_left
                - horizontal_padding,
            )

            right = min(
                page_right,
                content_right
                + horizontal_padding,
            )

            top = max(
                minimum_top,
                content_top
                - cls.REGION_PADDING,
            )

            bottom = min(
                maximum_bottom,
                content_bottom
                + cls.REGION_PADDING,
            )

        else:
            left = page_left
            right = page_right
            top = minimum_top
            bottom = maximum_bottom

        if right <= left:
            left = page_left
            right = page_right

        if bottom <= top:
            top = minimum_top
            bottom = maximum_bottom

        return (
            left,
            top,
            right,
            bottom,
        )

    # ---------------------------------------------------------
    # Column detection
    # ---------------------------------------------------------

    @classmethod
    def _detect_column_groups(
        cls,
        body_items: list[_ParagraphItem],
        body_bbox: Bounds,
    ) -> tuple[
        list[list[_ParagraphItem]],
        list[_ParagraphItem],
        float,
        str,
    ]:
        """
        Detect strong paragraph columns.

        Weak, ambiguous or vertically separated clusters are
        treated as one column.
        """

        if not body_items:
            return (
                [],
                [],
                0.0,
                "No body paragraphs were available.",
            )

        body_width = max(
            body_bbox[2]
            - body_bbox[0],
            1.0,
        )

        eligible_items = [
            item
            for item in body_items
            if cls._is_column_candidate(
                item=item,
                body_width=body_width,
            )
        ]

        if (
            len(eligible_items)
            < cls.MINIMUM_COLUMN_CANDIDATES
        ):
            return cls._single_column_result(
                body_items
            )

        left_tolerance = max(
            cls.MINIMUM_LEFT_EDGE_CLUSTER_TOLERANCE,
            body_width
            * cls.LEFT_EDGE_CLUSTER_TOLERANCE_RATIO,
        )

        raw_clusters = (
            cls._cluster_items_by_left_edge(
                items=eligible_items,
                tolerance=left_tolerance,
            )
        )

        raw_clusters = [
            cluster
            for cluster in raw_clusters
            if (
                len(cluster)
                >= cls.MINIMUM_COLUMN_PARAGRAPHS
            )
        ]

        if len(raw_clusters) < 2:
            return cls._single_column_result(
                body_items
            )

        merged_clusters = (
            cls._merge_nearby_left_clusters(
                clusters=raw_clusters,
                body_width=body_width,
                left_tolerance=left_tolerance,
            )
        )

        merged_clusters = [
            cluster
            for cluster in merged_clusters
            if (
                len(cluster)
                >= cls.MINIMUM_COLUMN_PARAGRAPHS
            )
        ]

        if len(merged_clusters) < 2:
            return cls._single_column_result(
                body_items
            )

        # Prefer the strongest clusters when many indentation
        # patterns were found.
        if (
            len(merged_clusters)
            > cls.MAXIMUM_COLUMN_COUNT
        ):
            merged_clusters = sorted(
                merged_clusters,
                key=lambda cluster: len(
                    cluster
                ),
                reverse=True,
            )[
                :cls.MAXIMUM_COLUMN_COUNT
            ]

        merged_clusters.sort(
            key=cls._cluster_left
        )

        boundaries: list[float] = []
        gutter_scores: list[float] = []
        overlap_scores: list[float] = []

        for index in range(
            len(merged_clusters) - 1
        ):
            left_cluster = (
                merged_clusters[index]
            )

            right_cluster = (
                merged_clusters[
                    index + 1
                ]
            )

            left_median = median([
                item.left
                for item in left_cluster
            ])

            right_median = median([
                item.left
                for item in right_cluster
            ])

            left_separation = (
                right_median
                - left_median
            )

            if (
                left_separation
                < body_width
                * cls.MINIMUM_COLUMN_LEFT_SEPARATION_RATIO
            ):
                return cls._single_column_result(
                    body_items
                )

            left_cluster_right = (
                cls._percentile(
                    [
                        item.right
                        for item in left_cluster
                    ],
                    0.80,
                )
            )

            right_cluster_left = (
                cls._percentile(
                    [
                        item.left
                        for item in right_cluster
                    ],
                    0.20,
                )
            )

            gutter_width = (
                right_cluster_left
                - left_cluster_right
            )

            minimum_gutter = max(
                cls.MINIMUM_GUTTER_POINTS,
                body_width
                * cls.MINIMUM_GUTTER_RATIO,
            )

            if gutter_width < minimum_gutter:
                return cls._single_column_result(
                    body_items
                )

            vertical_overlap_ratio = (
                cls._cluster_vertical_overlap(
                    left_cluster,
                    right_cluster,
                )
            )

            if (
                vertical_overlap_ratio
                < cls.MINIMUM_COLUMN_VERTICAL_OVERLAP
            ):
                return cls._single_column_result(
                    body_items
                )

            boundary = (
                left_cluster_right
                + right_cluster_left
            ) / 2.0

            boundaries.append(
                boundary
            )

            gutter_scores.append(
                min(
                    gutter_width
                    / max(
                        body_width * 0.10,
                        1.0,
                    ),
                    1.0,
                )
            )

            overlap_scores.append(
                min(
                    vertical_overlap_ratio,
                    1.0,
                )
            )

        assigned_groups: list[
            list[_ParagraphItem]
        ] = [
            []
            for _ in merged_clusters
        ]

        spanning_items: list[
            _ParagraphItem
        ] = []

        for item in body_items:
            crosses_boundary = any(
                (
                    item.left
                    + cls.COLUMN_BOUNDARY_TOLERANCE
                )
                < boundary
                < (
                    item.right
                    - cls.COLUMN_BOUNDARY_TOLERANCE
                )
                for boundary in boundaries
            )

            is_full_width = (
                item.width
                >= body_width
                * cls.SPANNING_PARAGRAPH_WIDTH_RATIO
            )

            if (
                crosses_boundary
                or is_full_width
            ):
                spanning_items.append(
                    item
                )

                continue

            group_index = 0

            for boundary in boundaries:
                if item.center_x > boundary:
                    group_index += 1

            assigned_groups[
                group_index
            ].append(
                item
            )

        if any(
            len(group)
            < cls.MINIMUM_COLUMN_PARAGRAPHS
            for group in assigned_groups
        ):
            return cls._single_column_result(
                body_items
            )

        group_sizes = [
            len(group)
            for group in assigned_groups
        ]

        balance_score = (
            min(group_sizes)
            / max(
                max(group_sizes),
                1,
            )
        )

        confidence = (
            0.40
            + cls._average(
                gutter_scores
            ) * 0.25
            + cls._average(
                overlap_scores
            ) * 0.25
            + balance_score * 0.10
        )

        confidence = cls._clamp(
            confidence
        )

        return (
            assigned_groups,
            spanning_items,
            confidence,
            (
                f"Detected {len(assigned_groups)} strong "
                "column groups using repeated left edges, "
                "horizontal gutters and vertical overlap."
            ),
        )

    @classmethod
    def _single_column_result(
        cls,
        body_items: list[_ParagraphItem],
    ) -> tuple[
        list[list[_ParagraphItem]],
        list[_ParagraphItem],
        float,
        str,
    ]:
        if not body_items:
            return (
                [],
                [],
                0.0,
                "No body content was available.",
            )

        return (
            [
                list(body_items)
            ],
            [],
            0.78,
            (
                "No reliable multi-column gutter was "
                "detected; body content is treated as one "
                "column."
            ),
        )

    @classmethod
    def _is_column_candidate(
        cls,
        item: _ParagraphItem,
        body_width: float,
    ) -> bool:
        if (
            len(item.text)
            < cls.MINIMUM_COLUMN_TEXT_LENGTH
        ):
            return False

        width_ratio = (
            item.width
            / max(
                body_width,
                1.0,
            )
        )

        return (
            cls.MINIMUM_PARAGRAPH_WIDTH_RATIO
            <= width_ratio
            <= cls.MAXIMUM_COLUMN_PARAGRAPH_WIDTH_RATIO
        )

    @classmethod
    def _cluster_items_by_left_edge(
        cls,
        items: list[_ParagraphItem],
        tolerance: float,
    ) -> list[list[_ParagraphItem]]:
        clusters: list[
            list[_ParagraphItem]
        ] = []

        for item in sorted(
            items,
            key=lambda value: value.left,
        ):
            best_cluster: (
                list[_ParagraphItem]
                | None
            ) = None

            best_distance: float | None = None

            for cluster in clusters:
                cluster_left = median([
                    member.left
                    for member in cluster
                ])

                distance = abs(
                    item.left
                    - cluster_left
                )

                if (
                    distance <= tolerance
                    and (
                        best_distance is None
                        or distance < best_distance
                    )
                ):
                    best_cluster = cluster
                    best_distance = distance

            if best_cluster is None:
                clusters.append(
                    [item]
                )

            else:
                best_cluster.append(
                    item
                )

        return clusters

    @classmethod
    def _merge_nearby_left_clusters(
        cls,
        clusters: list[
            list[_ParagraphItem]
        ],
        body_width: float,
        left_tolerance: float,
    ) -> list[
        list[_ParagraphItem]
    ]:
        if not clusters:
            return []

        sorted_clusters = sorted(
            clusters,
            key=cls._cluster_left,
        )

        merge_distance = max(
            left_tolerance * 1.50,
            body_width
            * cls.MERGE_CLUSTER_DISTANCE_RATIO,
        )

        merged: list[
            list[_ParagraphItem]
        ] = [
            list(
                sorted_clusters[0]
            )
        ]

        for cluster in sorted_clusters[1:]:
            current_left = (
                cls._cluster_left(
                    cluster
                )
            )

            previous_left = (
                cls._cluster_left(
                    merged[-1]
                )
            )

            if (
                current_left
                - previous_left
                <= merge_distance
            ):
                merged[-1].extend(
                    cluster
                )

            else:
                merged.append(
                    list(cluster)
                )

        return merged

    @staticmethod
    def _cluster_left(
        cluster: list[_ParagraphItem],
    ) -> float:
        return float(
            median([
                item.left
                for item in cluster
            ])
        )

    @staticmethod
    def _cluster_vertical_overlap(
        first: list[_ParagraphItem],
        second: list[_ParagraphItem],
    ) -> float:
        first_top = min(
            item.top
            for item in first
        )

        first_bottom = max(
            item.bottom
            for item in first
        )

        second_top = min(
            item.top
            for item in second
        )

        second_bottom = max(
            item.bottom
            for item in second
        )

        overlap = max(
            min(
                first_bottom,
                second_bottom,
            )
            - max(
                first_top,
                second_top,
            ),
            0.0,
        )

        smaller_height = max(
            min(
                first_bottom - first_top,
                second_bottom - second_top,
            ),
            1.0,
        )

        return (
            overlap
            / smaller_height
        )

    # ---------------------------------------------------------
    # Region membership
    # ---------------------------------------------------------

    @staticmethod
    def _attach_items_to_layout_region(
        region: LayoutRegion,
        items: Iterable[_ParagraphItem],
    ) -> None:
        for item in items:
            region.add_paragraph_region(
                item.number
            )

            for block_number in getattr(
                item.paragraph,
                "source_block_numbers",
                [],
            ) or []:
                try:
                    normalized_number = int(
                        block_number
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                region.add_source_block(
                    normalized_number
                )

    @staticmethod
    def _attach_items_to_column_region(
        region: ColumnRegion,
        items: Iterable[_ParagraphItem],
    ) -> None:
        for item in items:
            region.add_paragraph_region(
                item.number
            )

            for block_number in getattr(
                item.paragraph,
                "source_block_numbers",
                [],
            ) or []:
                try:
                    normalized_number = int(
                        block_number
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                region.add_source_block(
                    normalized_number
                )

    # ---------------------------------------------------------
    # Geometry utilities
    # ---------------------------------------------------------

    @classmethod
    def _items_bbox(
        cls,
        items: Iterable[_ParagraphItem],
        clip: Bounds,
        padding: float = 0.0,
    ) -> Bounds | None:
        item_list = list(
            items
        )

        if not item_list:
            return None

        left = min(
            item.left
            for item in item_list
        ) - padding

        top = min(
            item.top
            for item in item_list
        ) - padding

        right = max(
            item.right
            for item in item_list
        ) + padding

        bottom = max(
            item.bottom
            for item in item_list
        ) + padding

        bounds = (
            left,
            top,
            right,
            bottom,
        )

        return RectangleUnion.intersection(
            bounds,
            clip,
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

    @staticmethod
    def _percentile(
        values: list[float],
        ratio: float,
    ) -> float:
        if not values:
            return 0.0

        sorted_values = sorted(
            float(value)
            for value in values
        )

        ratio = max(
            0.0,
            min(
                float(ratio),
                1.0,
            ),
        )

        if len(sorted_values) == 1:
            return sorted_values[0]

        position = (
            len(sorted_values) - 1
        ) * ratio

        lower_index = int(
            position
        )

        upper_index = min(
            lower_index + 1,
            len(sorted_values) - 1,
        )

        fraction = (
            position
            - lower_index
        )

        return (
            sorted_values[lower_index]
            * (1.0 - fraction)
            + sorted_values[upper_index]
            * fraction
        )

    @staticmethod
    def _average(
        values: Iterable[float],
    ) -> float:
        normalized_values = [
            float(value)
            for value in values
        ]

        if not normalized_values:
            return 0.0

        return (
            sum(normalized_values)
            / len(normalized_values)
        )

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                float(value),
                1.0,
            ),
        )