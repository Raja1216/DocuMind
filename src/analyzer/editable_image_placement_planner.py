from __future__ import annotations

import hashlib
import math

from collections import Counter
from typing import Any

from src.models.editable_image import (
    EditableImage,
    EditableImageAnchorPosition,
    EditableImageDisposition,
    EditableImageHorizontalAlignment,
    EditableImagePlacement,
    EditableImageRole,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableImagePlacementPlanner:
    """
    Determine semantic role and Word placement for normalized
    image placements.

    The planner uses only generalized document evidence:

    - page coverage;
    - position within the page;
    - repetition across pages;
    - opacity;
    - text and table overlap;
    - nearby paragraph geometry;
    - side-by-side layout evidence.

    It does not render images or change render-plan ownership.
    """

    BACKGROUND_PAGE_AREA_RATIO = 0.70

    WATERMARK_MINIMUM_AREA_RATIO = 0.12

    WATERMARK_MINIMUM_TEXT_OVERLAP = 0.25

    WATERMARK_MAXIMUM_OPACITY = 0.70

    LOGO_MAXIMUM_AREA_RATIO = 0.12

    DECORATION_MAXIMUM_AREA_RATIO = 0.003

    OVERLAY_TEXT_OVERLAP_RATIO = 0.18

    HEADER_FOOTER_BAND_RATIO = 0.18

    CENTER_TOLERANCE_RATIO = 0.18

    ALIGNMENT_TOLERANCE_RATIO = 0.05

    SIDE_BY_SIDE_VERTICAL_OVERLAP = 0.40

    SIDE_BY_SIDE_MAXIMUM_GAP_RATIO = 0.08

    GEOMETRY_TOLERANCE = 0.01

    PLANNER_MESSAGE_PREFIX = (
        "[image-placement] "
    )

    @classmethod
    def plan_document(
        cls,
        document,
    ) -> None:
        pages = list(
            getattr(
                document,
                "pages",
                [],
            )
            or []
        )

        repetition_counts = Counter()

        for page in pages:
            for image in getattr(
                page,
                "editable_images",
                [],
            ) or []:
                repetition_key = (
                    cls._repetition_key(
                        image
                    )
                )

                if repetition_key is not None:
                    repetition_counts[
                        repetition_key
                    ] += 1

        for page in pages:
            cls.plan_page(
                page=page,
                repetition_counts=(
                    repetition_counts
                ),
            )

    @classmethod
    def plan_page(
        cls,
        *,
        page,
        repetition_counts=None,
    ) -> list[EditableImage]:
        images = list(
            getattr(
                page,
                "editable_images",
                [],
            )
            or []
        )

        if repetition_counts is None:
            repetition_counts = Counter()

            for image in images:
                key = cls._repetition_key(
                    image
                )

                if key is not None:
                    repetition_counts[
                        key
                    ] += 1

        page_bbox = cls._rectangle_from(
            getattr(
                page,
                "bbox",
                page,
            )
        )

        text_regions = (
            cls._collect_text_regions(
                page
            )
        )

        table_rectangles = (
            cls._collect_table_rectangles(
                page
            )
        )

        for image in images:
            cls._plan_image(
                image=image,
                page_bbox=page_bbox,
                text_regions=text_regions,
                table_rectangles=(
                    table_rectangles
                ),
                repetition_counts=(
                    repetition_counts
                ),
            )

        return images

    @classmethod
    def _plan_image(
        cls,
        *,
        image: EditableImage,
        page_bbox: Rectangle | None,
        text_regions: list[
            tuple[
                Any,
                Rectangle,
                bool,
            ]
        ],
        table_rectangles: list[
            Rectangle
        ],
        repetition_counts,
    ) -> None:
        cls._reset_planner_state(
            image
        )

        if (
            image.disposition
            == EditableImageDisposition.SKIP
            or not image.has_valid_geometry
            or page_bbox is None
            or not cls._rectangle_has_area(
                page_bbox
            )
        ):
            image.add_warning(
                cls.PLANNER_MESSAGE_PREFIX
                + (
                    "Placement planning was skipped "
                    "because image or page geometry "
                    "is invalid."
                )
            )

            return

        page_area = max(
            cls._rectangle_area(
                page_bbox
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        image_area = max(
            cls._rectangle_area(
                image.bbox
            ),
            0.0,
        )

        image.page_area_ratio = min(
            image_area / page_area,
            1.0,
        )

        image.text_overlap_ratio = (
            cls._combined_overlap_ratio(
                source=image.bbox,
                rectangles=[
                    rectangle
                    for (
                        _,
                        rectangle,
                        _,
                    ) in text_regions
                ],
            )
        )

        image.table_overlap_ratio = (
            cls._combined_overlap_ratio(
                source=image.bbox,
                rectangles=(
                    table_rectangles
                ),
            )
        )

        repetition_key = (
            cls._repetition_key(
                image
            )
        )

        if repetition_key is not None:
            image.repeat_count = max(
                int(
                    repetition_counts.get(
                        repetition_key,
                        1,
                    )
                ),
                1,
            )
        else:
            image.repeat_count = 1

        image.horizontal_alignment = (
            cls._resolve_horizontal_alignment(
                image_bbox=image.bbox,
                page_bbox=page_bbox,
            )
        )

        anchor = cls._resolve_anchor(
            image_bbox=image.bbox,
            text_regions=text_regions,
        )

        if anchor is not None:
            (
                anchor_number,
                anchor_position,
                _,
            ) = anchor

            image.anchor_paragraph_region_number = (
                anchor_number
            )

            image.anchor_position = (
                anchor_position
            )

        image.role = cls._resolve_role(
            image=image,
            page_bbox=page_bbox,
        )

        has_side_by_side_text = (
            cls._has_side_by_side_text(
                image_bbox=image.bbox,
                page_bbox=page_bbox,
                text_regions=text_regions,
            )
        )

        image.placement = (
            cls._resolve_placement(
                image=image,
                has_side_by_side_text=(
                    has_side_by_side_text
                ),
            )
        )

        image.placement_confidence = (
            cls._resolve_placement_confidence(
                image=image,
                has_side_by_side_text=(
                    has_side_by_side_text
                ),
            )
        )

        image.add_reason(
            cls.PLANNER_MESSAGE_PREFIX
            + (
                f"Role={image.role.value}; "
                f"placement="
                f"{image.placement.value}; "
                f"page-area="
                f"{image.page_area_ratio:.3f}; "
                f"text-overlap="
                f"{image.text_overlap_ratio:.3f}; "
                f"repeat-count="
                f"{image.repeat_count}."
            )
        )

        if (
            image.placement
            == EditableImagePlacement.INLINE
            and image
            .anchor_paragraph_region_number
            is None
        ):
            image.add_warning(
                cls.PLANNER_MESSAGE_PREFIX
                + (
                    "Inline placement has no reliable "
                    "paragraph-region anchor."
                )
            )

            image.placement = (
                EditableImagePlacement.FLOATING
            )

    # ---------------------------------------------------------
    # Role and placement
    # ---------------------------------------------------------

    @classmethod
    def _resolve_role(
        cls,
        *,
        image: EditableImage,
        page_bbox: Rectangle,
    ) -> EditableImageRole:
        if (
            image.page_area_ratio
            >= cls.BACKGROUND_PAGE_AREA_RATIO
        ):
            return (
                EditableImageRole.BACKGROUND
            )

        if (
            image.page_area_ratio
            >= cls
            .WATERMARK_MINIMUM_AREA_RATIO
            and image.text_overlap_ratio
            >= cls
            .WATERMARK_MINIMUM_TEXT_OVERLAP
            and image.opacity
            <= cls.WATERMARK_MAXIMUM_OPACITY
            and cls._is_page_centered(
                image_bbox=image.bbox,
                page_bbox=page_bbox,
            )
        ):
            return (
                EditableImageRole.WATERMARK
            )

        if (
            image.repeat_count >= 2
            and image.page_area_ratio
            <= cls.LOGO_MAXIMUM_AREA_RATIO
            and cls._is_in_header_or_footer_band(
                image_bbox=image.bbox,
                page_bbox=page_bbox,
            )
        ):
            return EditableImageRole.LOGO

        if (
            image.page_area_ratio
            <= cls.DECORATION_MAXIMUM_AREA_RATIO
            and image.text_overlap_ratio
            < cls.OVERLAY_TEXT_OVERLAP_RATIO
        ):
            return (
                EditableImageRole.DECORATION
            )

        return EditableImageRole.CONTENT

    @classmethod
    def _resolve_placement(
        cls,
        *,
        image: EditableImage,
        has_side_by_side_text: bool,
    ) -> EditableImagePlacement:
        if image.role in {
            EditableImageRole.BACKGROUND,
            EditableImageRole.WATERMARK,
        }:
            return (
                EditableImagePlacement.BACKGROUND
            )

        if image.role == EditableImageRole.LOGO:
            return (
                EditableImagePlacement.FLOATING
            )

        if (
            image.role
            == EditableImageRole.DECORATION
        ):
            if (
                image.text_overlap_ratio
                >= cls
                .OVERLAY_TEXT_OVERLAP_RATIO
            ):
                return (
                    EditableImagePlacement.OVERLAY
                )

            return (
                EditableImagePlacement.FLOATING
            )

        if (
            image.text_overlap_ratio
            >= cls.OVERLAY_TEXT_OVERLAP_RATIO
        ):
            return (
                EditableImagePlacement.OVERLAY
            )

        if has_side_by_side_text:
            return (
                EditableImagePlacement.FLOATING
            )

        if (
            image.anchor_paragraph_region_number
            is not None
        ):
            return (
                EditableImagePlacement.INLINE
            )

        return EditableImagePlacement.FLOATING

    @classmethod
    def _resolve_placement_confidence(
        cls,
        *,
        image: EditableImage,
        has_side_by_side_text: bool,
    ) -> float:
        decision_score = 0.50

        if image.role != EditableImageRole.UNKNOWN:
            decision_score += 0.15

        if (
            image.placement
            != EditableImagePlacement.UNRESOLVED
        ):
            decision_score += 0.15

        if (
            image.placement
            == EditableImagePlacement.INLINE
            and image
            .anchor_paragraph_region_number
            is not None
        ):
            decision_score += 0.10

        if (
            image.role == EditableImageRole.LOGO
            and image.repeat_count >= 2
        ):
            decision_score += 0.10

        if (
            image.role
            in {
                EditableImageRole.BACKGROUND,
                EditableImageRole.WATERMARK,
            }
        ):
            decision_score += 0.10

        if has_side_by_side_text:
            decision_score += 0.05

        decision_score = min(
            decision_score,
            1.0,
        )

        return max(
            0.0,
            min(
                0.60 * image.confidence
                + 0.40 * decision_score,
                1.0,
            ),
        )

    # ---------------------------------------------------------
    # Paragraph anchoring
    # ---------------------------------------------------------

    @classmethod
    def _resolve_anchor(
        cls,
        *,
        image_bbox: Rectangle,
        text_regions: list[
            tuple[
                Any,
                Rectangle,
                bool,
            ]
        ],
    ) -> tuple[
        int,
        EditableImageAnchorPosition,
        float,
    ] | None:
        previous_candidates = []

        following_candidates = []

        for (
            region,
            rectangle,
            is_flow_region,
        ) in text_regions:
            if not is_flow_region:
                continue

            region_number = (
                cls._resolve_region_number(
                    region
                )
            )

            if region_number is None:
                continue

            if (
                float(
                    rectangle.bottom
                )
                <= float(
                    image_bbox.top
                )
                + cls.GEOMETRY_TOLERANCE
            ):
                distance = max(
                    float(
                        image_bbox.top
                    )
                    - float(
                        rectangle.bottom
                    ),
                    0.0,
                )

                previous_candidates.append(
                    (
                        distance,
                        region_number,
                    )
                )

            if (
                float(
                    rectangle.top
                )
                >= float(
                    image_bbox.bottom
                )
                - cls.GEOMETRY_TOLERANCE
            ):
                distance = max(
                    float(
                        rectangle.top
                    )
                    - float(
                        image_bbox.bottom
                    ),
                    0.0,
                )

                following_candidates.append(
                    (
                        distance,
                        region_number,
                    )
                )

        previous = (
            min(
                previous_candidates,
                default=None,
            )
        )

        following = (
            min(
                following_candidates,
                default=None,
            )
        )

        if previous is None and following is None:
            return None

        if following is None:
            return (
                previous[1],
                EditableImageAnchorPosition
                .AFTER,
                previous[0],
            )

        if previous is None:
            return (
                following[1],
                EditableImageAnchorPosition
                .BEFORE,
                following[0],
            )

        if following[0] <= previous[0]:
            return (
                following[1],
                EditableImageAnchorPosition
                .BEFORE,
                following[0],
            )

        return (
            previous[1],
            EditableImageAnchorPosition.AFTER,
            previous[0],
        )

    @staticmethod
    def _resolve_region_number(
        region,
    ) -> int | None:
        for attribute_name in (
            "number",
            "region_number",
            "paragraph_number",
            "id",
        ):
            value = getattr(
                region,
                attribute_name,
                None,
            )

            try:
                normalized = int(
                    value
                )
            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if normalized >= 0:
                return normalized

        return None

    # ---------------------------------------------------------
    # Layout evidence
    # ---------------------------------------------------------

    @classmethod
    def _resolve_horizontal_alignment(
        cls,
        *,
        image_bbox: Rectangle,
        page_bbox: Rectangle,
    ) -> EditableImageHorizontalAlignment:
        page_width = max(
            float(
                page_bbox.right
            )
            - float(
                page_bbox.left
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        tolerance = (
            page_width
            * cls.ALIGNMENT_TOLERANCE_RATIO
        )

        image_center = (
            float(
                image_bbox.left
            )
            + float(
                image_bbox.right
            )
        ) / 2.0

        page_center = (
            float(
                page_bbox.left
            )
            + float(
                page_bbox.right
            )
        ) / 2.0

        if (
            abs(
                image_center
                - page_center
            )
            <= tolerance
        ):
            return (
                EditableImageHorizontalAlignment
                .CENTER
            )

        if (
            abs(
                float(
                    image_bbox.left
                )
                - float(
                    page_bbox.left
                )
            )
            <= tolerance
        ):
            return (
                EditableImageHorizontalAlignment
                .LEFT
            )

        if (
            abs(
                float(
                    image_bbox.right
                )
                - float(
                    page_bbox.right
                )
            )
            <= tolerance
        ):
            return (
                EditableImageHorizontalAlignment
                .RIGHT
            )

        return (
            EditableImageHorizontalAlignment
            .ABSOLUTE
        )

    @classmethod
    def _has_side_by_side_text(
        cls,
        *,
        image_bbox: Rectangle,
        page_bbox: Rectangle,
        text_regions: list[
            tuple[
                Any,
                Rectangle,
                bool,
            ]
        ],
    ) -> bool:
        page_width = max(
            float(
                page_bbox.right
            )
            - float(
                page_bbox.left
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        maximum_gap = (
            page_width
            * cls
            .SIDE_BY_SIDE_MAXIMUM_GAP_RATIO
        )

        for (
            _,
            rectangle,
            is_flow_region,
        ) in text_regions:
            if not is_flow_region:
                continue

            vertical_overlap = (
                cls._vertical_overlap_ratio(
                    image_bbox,
                    rectangle,
                )
            )

            if (
                vertical_overlap
                < cls
                .SIDE_BY_SIDE_VERTICAL_OVERLAP
            ):
                continue

            if (
                float(
                    rectangle.right
                )
                <= float(
                    image_bbox.left
                )
            ):
                gap = (
                    float(
                        image_bbox.left
                    )
                    - float(
                        rectangle.right
                    )
                )

            elif (
                float(
                    rectangle.left
                )
                >= float(
                    image_bbox.right
                )
            ):
                gap = (
                    float(
                        rectangle.left
                    )
                    - float(
                        image_bbox.right
                    )
                )

            else:
                continue

            if gap <= maximum_gap:
                return True

        return False

    @classmethod
    def _is_in_header_or_footer_band(
        cls,
        *,
        image_bbox: Rectangle,
        page_bbox: Rectangle,
    ) -> bool:
        page_height = max(
            float(
                page_bbox.bottom
            )
            - float(
                page_bbox.top
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        header_bottom = (
            float(
                page_bbox.top
            )
            + page_height
            * cls.HEADER_FOOTER_BAND_RATIO
        )

        footer_top = (
            float(
                page_bbox.bottom
            )
            - page_height
            * cls.HEADER_FOOTER_BAND_RATIO
        )

        image_center_y = (
            float(
                image_bbox.top
            )
            + float(
                image_bbox.bottom
            )
        ) / 2.0

        return (
            image_center_y <= header_bottom
            or image_center_y >= footer_top
        )

    @classmethod
    def _is_page_centered(
        cls,
        *,
        image_bbox: Rectangle,
        page_bbox: Rectangle,
    ) -> bool:
        page_width = max(
            float(
                page_bbox.right
            )
            - float(
                page_bbox.left
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        page_height = max(
            float(
                page_bbox.bottom
            )
            - float(
                page_bbox.top
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        image_center_x = (
            float(
                image_bbox.left
            )
            + float(
                image_bbox.right
            )
        ) / 2.0

        image_center_y = (
            float(
                image_bbox.top
            )
            + float(
                image_bbox.bottom
            )
        ) / 2.0

        page_center_x = (
            float(
                page_bbox.left
            )
            + float(
                page_bbox.right
            )
        ) / 2.0

        page_center_y = (
            float(
                page_bbox.top
            )
            + float(
                page_bbox.bottom
            )
        ) / 2.0

        return (
            abs(
                image_center_x
                - page_center_x
            )
            <= page_width
            * cls.CENTER_TOLERANCE_RATIO
            and abs(
                image_center_y
                - page_center_y
            )
            <= page_height
            * cls.CENTER_TOLERANCE_RATIO
        )

    # ---------------------------------------------------------
    # Source collection
    # ---------------------------------------------------------

    @classmethod
    def _collect_text_regions(
        cls,
        page,
    ) -> list[
        tuple[
            Any,
            Rectangle,
            bool,
        ]
    ]:
        result = []

        source_regions = []

        for collection_name in (
            "paragraph_regions",
            "paragraphs",
        ):
            collection = getattr(
                page,
                collection_name,
                None,
            )

            if collection:
                source_regions = list(
                    collection
                )

                break

        for region in source_regions:
            rectangle = cls._rectangle_from(
                region
            )

            if (
                rectangle is None
                or not cls._rectangle_has_area(
                    rectangle
                )
            ):
                continue

            role = str(
                getattr(
                    getattr(
                        region,
                        "role",
                        None,
                    ),
                    "value",
                    getattr(
                        region,
                        "role",
                        "",
                    ),
                )
                or ""
            ).casefold()

            is_header = bool(
                getattr(
                    region,
                    "is_header",
                    False,
                )
            )

            is_footer = bool(
                getattr(
                    region,
                    "is_footer",
                    False,
                )
            )

            is_flow_region = (
                not is_header
                and not is_footer
                and role
                not in {
                    "header",
                    "footer",
                    "decoration",
                    "background",
                }
            )

            result.append(
                (
                    region,
                    rectangle,
                    is_flow_region,
                )
            )

        return result

    @classmethod
    def _collect_table_rectangles(
        cls,
        page,
    ) -> list[Rectangle]:
        result = []

        source_tables = (
            getattr(
                page,
                "editable_tables",
                None,
            )
            or getattr(
                page,
                "tables",
                [],
            )
            or []
        )

        for table in source_tables:
            rectangle = cls._rectangle_from(
                table
            )

            if (
                rectangle is not None
                and cls._rectangle_has_area(
                    rectangle
                )
            ):
                result.append(
                    rectangle
                )

        return result

    # ---------------------------------------------------------
    # Repetition
    # ---------------------------------------------------------

    @staticmethod
    def _repetition_key(
        image: EditableImage,
    ):
        if image.xref is not None:
            return (
                "xref",
                image.xref,
            )

        if image.payload:
            digest = hashlib.sha1(
                image.payload
            ).hexdigest()

            return (
                "payload",
                digest,
            )

        return None

    # ---------------------------------------------------------
    # Geometry helpers
    # ---------------------------------------------------------

    @staticmethod
    def _rectangle_from(
        source,
    ) -> Rectangle | None:
        if source is None:
            return None

        geometry_source = getattr(
            source,
            "bbox",
            source,
        )

        coordinate_groups = (
            (
                "left",
                "top",
                "right",
                "bottom",
            ),
            (
                "x0",
                "y0",
                "x1",
                "y1",
            ),
        )

        for (
            left_name,
            top_name,
            right_name,
            bottom_name,
        ) in coordinate_groups:
            try:
                left = float(
                    getattr(
                        geometry_source,
                        left_name,
                    )
                )

                top = float(
                    getattr(
                        geometry_source,
                        top_name,
                    )
                )

                right = float(
                    getattr(
                        geometry_source,
                        right_name,
                    )
                )

                bottom = float(
                    getattr(
                        geometry_source,
                        bottom_name,
                    )
                )

            except (
                AttributeError,
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if not all(
                math.isfinite(
                    value
                )
                for value in (
                    left,
                    top,
                    right,
                    bottom,
                )
            ):
                continue

            if right < left:
                left, right = (
                    right,
                    left,
                )

            if bottom < top:
                top, bottom = (
                    bottom,
                    top,
                )

            return Rectangle(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            )

        return None

    @classmethod
    def _rectangle_has_area(
        cls,
        rectangle: Rectangle,
    ) -> bool:
        return (
            cls._rectangle_area(
                rectangle
            )
            > cls.GEOMETRY_TOLERANCE
        )

    @staticmethod
    def _rectangle_area(
        rectangle: Rectangle,
    ) -> float:
        return max(
            float(
                rectangle.right
            )
            - float(
                rectangle.left
            ),
            0.0,
        ) * max(
            float(
                rectangle.bottom
            )
            - float(
                rectangle.top
            ),
            0.0,
        )

    @classmethod
    def _combined_overlap_ratio(
        cls,
        *,
        source: Rectangle,
        rectangles: list[Rectangle],
    ) -> float:
        source_area = max(
            cls._rectangle_area(
                source
            ),
            cls.GEOMETRY_TOLERANCE,
        )

        overlapping_area = sum(
            cls._intersection_area(
                source,
                rectangle,
            )
            for rectangle in rectangles
        )

        return min(
            overlapping_area / source_area,
            1.0,
        )

    @staticmethod
    def _intersection_area(
        first: Rectangle,
        second: Rectangle,
    ) -> float:
        left = max(
            float(
                first.left
            ),
            float(
                second.left
            ),
        )

        top = max(
            float(
                first.top
            ),
            float(
                second.top
            ),
        )

        right = min(
            float(
                first.right
            ),
            float(
                second.right
            ),
        )

        bottom = min(
            float(
                first.bottom
            ),
            float(
                second.bottom
            ),
        )

        return max(
            right - left,
            0.0,
        ) * max(
            bottom - top,
            0.0,
        )

    @staticmethod
    def _vertical_overlap_ratio(
        first: Rectangle,
        second: Rectangle,
    ) -> float:
        overlap = max(
            min(
                float(
                    first.bottom
                ),
                float(
                    second.bottom
                ),
            )
            - max(
                float(
                    first.top
                ),
                float(
                    second.top
                ),
            ),
            0.0,
        )

        minimum_height = max(
            min(
                float(
                    first.bottom
                )
                - float(
                    first.top
                ),
                float(
                    second.bottom
                )
                - float(
                    second.top
                ),
            ),
            EditableImagePlacementPlanner
            .GEOMETRY_TOLERANCE,
        )

        return min(
            overlap / minimum_height,
            1.0,
        )

    # ---------------------------------------------------------
    # Reanalysis
    # ---------------------------------------------------------

    @classmethod
    def _reset_planner_state(
        cls,
        image: EditableImage,
    ) -> None:
        image.role = EditableImageRole.UNKNOWN

        image.placement = (
            EditableImagePlacement.UNRESOLVED
        )

        image.anchor_paragraph_region_number = (
            None
        )

        image.anchor_position = (
            EditableImageAnchorPosition.NONE
        )

        image.horizontal_alignment = (
            EditableImageHorizontalAlignment
            .ABSOLUTE
        )

        image.placement_confidence = 0.0

        image.page_area_ratio = 0.0

        image.text_overlap_ratio = 0.0

        image.table_overlap_ratio = 0.0

        image.repeat_count = 1

        image.reasons = [
            reason
            for reason in image.reasons
            if not reason.startswith(
                cls.PLANNER_MESSAGE_PREFIX
            )
        ]

        image.warnings = [
            warning
            for warning in image.warnings
            if not warning.startswith(
                cls.PLANNER_MESSAGE_PREFIX
            )
        ]