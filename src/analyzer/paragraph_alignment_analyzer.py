from __future__ import annotations

from dataclasses import dataclass
from statistics import median, pstdev
from typing import Any, Iterable

from src.models.column_region import ColumnRegion
from src.models.document import Document
from src.models.geometry.rectangle import Rectangle
from src.models.layout_region import (
    LayoutRegion,
    LayoutRegionType,
)
from src.models.page import Page
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
    ParagraphAlignmentResult,
)
from src.utils.rectangle_union import (
    Bounds,
    RectangleUnion,
)


@dataclass(slots=True)
class _LineGeometry:
    """
    Internal representation of one visible paragraph line.
    """

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
    def width(self) -> float:
        return max(
            self.right - self.left,
            0.0,
        )

    @property
    def center_x(self) -> float:
        return (
            self.left + self.right
        ) / 2.0


class ParagraphAlignmentAnalyzer:
    """
    Detects paragraph alignment relative to the paragraph's
    nearest meaningful layout container.

    This analyzer must not contain:

        filename-specific conditions;
        page-number-specific conditions;
        sample-PDF-specific conditions.
    """

    # ---------------------------------------------------------
    # General tolerances
    # ---------------------------------------------------------

    MINIMUM_REFERENCE_WIDTH = 1.0

    MINIMUM_ABSOLUTE_EDGE_TOLERANCE = 3.0
    EDGE_TOLERANCE_RATIO = 0.015

    MINIMUM_SIDE_GAP_TOLERANCE = 6.0
    SIDE_GAP_TOLERANCE_RATIO = 0.035

    MINIMUM_CENTER_TOLERANCE = 6.0
    CENTER_TOLERANCE_RATIO = 0.035

    GAP_BALANCE_TOLERANCE_RATIO = 0.04

    # ---------------------------------------------------------
    # Centered alignment
    # ---------------------------------------------------------

    CENTER_MAXIMUM_WIDTH_RATIO = 0.90

    CENTER_MAXIMUM_LINE_CENTER_VARIANCE_RATIO = 0.035

    # ---------------------------------------------------------
    # Left/right alignment
    # ---------------------------------------------------------

    SIDE_ALIGNMENT_MINIMUM_GAP_DIFFERENCE_RATIO = 0.06

    SIDE_ALIGNMENT_MAXIMUM_EDGE_VARIANCE_RATIO = 0.025

    # ---------------------------------------------------------
    # Justified alignment
    # ---------------------------------------------------------

    JUSTIFY_MINIMUM_LINE_COUNT = 2

    JUSTIFY_MINIMUM_NONFINAL_WIDTH_RATIO = 0.72

    JUSTIFY_MAXIMUM_EDGE_VARIANCE_RATIO = 0.025

    JUSTIFY_MAXIMUM_LAST_LINE_REFERENCE_RATIO = 0.86

    JUSTIFY_MAXIMUM_LAST_LINE_RELATIVE_RATIO = 0.90

    # ---------------------------------------------------------
    # Hanging indentation
    # ---------------------------------------------------------

    MINIMUM_HANGING_INDENT = 8.0

    HANGING_INDENT_RATIO = 0.025

    # ---------------------------------------------------------
    # Region matching
    # ---------------------------------------------------------

    MINIMUM_REGION_OVERLAP_RATIO = 0.65

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> None:
        """
        Analyze paragraph alignment on every page.
        """

        for page in document.pages:
            cls.analyze_page(
                page
            )

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> list[ParagraphAlignmentResult]:
        """
        Analyze every visible paragraph on one page.

        Reanalysis clears all previous alignment results and
        paragraph alignment metadata.
        """

        page.paragraph_alignment_results.clear()

        used_region_numbers: set[int] = set()

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
            cls._reset_paragraph_alignment(
                paragraph
            )

            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            paragraph_bbox = (
                cls._resolve_paragraph_bbox(
                    paragraph
                )
            )

            if paragraph_bbox is None:
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

            while region_number in used_region_numbers:
                region_number += 1

            used_region_numbers.add(
                region_number
            )

            line_geometries = (
                cls._collect_line_geometries(
                    paragraph=paragraph,
                    paragraph_bbox=paragraph_bbox,
                )
            )

            (
                reference_type,
                reference_id,
                reference_bbox,
            ) = cls._resolve_reference_container(
                page=page,
                paragraph=paragraph,
                paragraph_region_number=(
                    region_number
                ),
                paragraph_bbox=paragraph_bbox,
            )

            result = (
                cls._analyze_paragraph_geometry(
                    page_number=page.number,
                    paragraph_region_number=(
                        region_number
                    ),
                    paragraph=paragraph,
                    paragraph_bbox=(
                        paragraph_bbox
                    ),
                    line_geometries=(
                        line_geometries
                    ),
                    reference_type=(
                        reference_type
                    ),
                    reference_id=(
                        reference_id
                    ),
                    reference_bbox=(
                        reference_bbox
                    ),
                )
            )

            page.paragraph_alignment_results.append(
                result
            )

            cls._assign_result_to_paragraph(
                paragraph=paragraph,
                result=result,
            )

        return page.paragraph_alignment_results

    # ---------------------------------------------------------
    # Alignment analysis
    # ---------------------------------------------------------

    @classmethod
    def _analyze_paragraph_geometry(
        cls,
        page_number: int,
        paragraph_region_number: int,
        paragraph: Any,
        paragraph_bbox: Bounds,
        line_geometries: list[_LineGeometry],
        reference_type: AlignmentReferenceType,
        reference_id: int | None,
        reference_bbox: Bounds,
    ) -> ParagraphAlignmentResult:
        result = ParagraphAlignmentResult(
            page_number=page_number,
            paragraph_region_number=(
                paragraph_region_number
            ),
            reference_type=reference_type,
            reference_id=reference_id,
            paragraph_bbox=cls._make_rectangle(
                paragraph_bbox
            ),
            reference_bbox=cls._make_rectangle(
                reference_bbox
            ),
        )

        paragraph_left = paragraph_bbox[0]
        paragraph_right = paragraph_bbox[2]

        paragraph_width = max(
            paragraph_right - paragraph_left,
            0.0,
        )

        paragraph_center = (
            paragraph_left
            + paragraph_right
        ) / 2.0

        reference_left = reference_bbox[0]
        reference_right = reference_bbox[2]

        reference_width = max(
            reference_right
            - reference_left,
            0.0,
        )

        reference_center = (
            reference_left
            + reference_right
        ) / 2.0

        result.left_gap = max(
            paragraph_left
            - reference_left,
            0.0,
        )

        result.right_gap = max(
            reference_right
            - paragraph_right,
            0.0,
        )

        result.center_offset = (
            paragraph_center
            - reference_center
        )

        if reference_width > 0.0:
            result.set_width_ratio(
                paragraph_width
                / reference_width
            )

        result.line_count = len(
            line_geometries
        )

        line_left_edges = [
            line.left
            for line in line_geometries
        ]

        line_right_edges = [
            line.right
            for line in line_geometries
        ]

        line_widths = [
            line.width
            for line in line_geometries
        ]

        line_centers = [
            line.center_x
            for line in line_geometries
        ]

        result.left_edge_variance = (
            cls._standard_deviation(
                line_left_edges
            )
        )

        result.right_edge_variance = (
            cls._standard_deviation(
                line_right_edges
            )
        )

        if line_widths and reference_width > 0.0:
            result.set_last_line_width_ratio(
                line_widths[-1]
                / reference_width
            )

        if len(line_widths) >= 2:
            previous_width = median(
                line_widths[:-1]
            )

            if previous_width > 0.0:
                result.set_last_line_relative_width(
                    line_widths[-1]
                    / previous_width
                )

        elif line_widths:
            result.set_last_line_relative_width(
                1.0
            )

        result.has_hanging_indent = (
            cls._detect_hanging_indent(
                paragraph=paragraph,
                lines=line_geometries,
                reference_left=(
                    reference_left
                ),
                reference_width=(
                    reference_width
                ),
            )
        )

        if (
            reference_width
            < cls.MINIMUM_REFERENCE_WIDTH
        ):
            result.alignment = (
                ParagraphAlignment.UNKNOWN
            )

            result.set_confidence(
                0.0
            )

            result.add_warning(
                (
                    "The alignment reference container "
                    "has no usable width."
                )
            )

            return result

        edge_tolerance = max(
            cls.MINIMUM_ABSOLUTE_EDGE_TOLERANCE,
            reference_width
            * cls.EDGE_TOLERANCE_RATIO,
        )

        side_gap_tolerance = max(
            cls.MINIMUM_SIDE_GAP_TOLERANCE,
            reference_width
            * cls.SIDE_GAP_TOLERANCE_RATIO,
        )

        center_tolerance = max(
            cls.MINIMUM_CENTER_TOLERANCE,
            reference_width
            * cls.CENTER_TOLERANCE_RATIO,
        )

        gap_balance_tolerance = max(
            cls.MINIMUM_CENTER_TOLERANCE,
            reference_width
            * cls.GAP_BALANCE_TOLERANCE_RATIO,
        )

        line_center_variance = (
            cls._standard_deviation(
                line_centers
            )
        )

        is_list_paragraph = (
            cls._is_list_paragraph(
                paragraph
            )
        )

        # -----------------------------------------------------
        # 1. Justified
        # -----------------------------------------------------

        if cls._looks_justified(
            result=result,
            line_geometries=(
                line_geometries
            ),
            reference_width=(
                reference_width
            ),
            edge_tolerance=(
                edge_tolerance
            ),
            side_gap_tolerance=(
                side_gap_tolerance
            ),
        ):
            result.alignment = (
                ParagraphAlignment.JUSTIFY
            )

            confidence = (
                cls._justify_confidence(
                    result=result,
                    reference_width=(
                        reference_width
                    ),
                )
            )

            result.set_confidence(
                confidence
            )

            result.add_reason(
                (
                    "Non-final lines share stable left "
                    "and right edges."
                )
            )

            result.add_reason(
                (
                    "The final line is shorter than the "
                    "preceding paragraph lines."
                )
            )

            return result

        # -----------------------------------------------------
        # 2. Lists and hanging indentation
        #
        # Lists should not be mistaken for centered or
        # right-aligned text because of their marker offset.
        # -----------------------------------------------------

        if (
            is_list_paragraph
            or result.has_hanging_indent
        ):
            result.alignment = (
                ParagraphAlignment.LEFT
            )

            confidence = (
                0.78
                if (
                    result.left_edge_variance
                    <= edge_tolerance * 2.0
                )
                else 0.66
            )

            result.set_confidence(
                confidence
            )

            result.add_reason(
                (
                    "List-marker or hanging-indent "
                    "evidence indicates left alignment."
                )
            )

            return result

        # -----------------------------------------------------
        # 3. Centered
        # -----------------------------------------------------

        gap_difference = abs(
            result.left_gap
            - result.right_gap
        )

        centered_by_container = (
            result.absolute_center_offset
            <= center_tolerance
            and gap_difference
            <= gap_balance_tolerance
            and result.width_ratio
            <= cls.CENTER_MAXIMUM_WIDTH_RATIO
        )

        centered_by_lines = (
            line_center_variance
            <= max(
                center_tolerance,
                reference_width
                * cls
                .CENTER_MAXIMUM_LINE_CENTER_VARIANCE_RATIO,
            )
        )

        if (
            centered_by_container
            and centered_by_lines
        ):
            result.alignment = (
                ParagraphAlignment.CENTER
            )

            center_score = max(
                0.0,
                1.0
                - (
                    result.absolute_center_offset
                    / max(
                        center_tolerance,
                        1.0,
                    )
                ),
            )

            balance_score = max(
                0.0,
                1.0
                - (
                    gap_difference
                    / max(
                        gap_balance_tolerance,
                        1.0,
                    )
                ),
            )

            confidence = (
                0.55
                + center_score * 0.25
                + balance_score * 0.20
            )

            result.set_confidence(
                confidence
            )

            result.add_reason(
                (
                    "Paragraph and line centers align "
                    "with the reference-container center."
                )
            )

            result.add_reason(
                (
                    "Left and right container gaps are "
                    "balanced."
                )
            )

            return result

        # -----------------------------------------------------
        # 4. Right-aligned
        # -----------------------------------------------------

        minimum_gap_difference = (
            reference_width
            * cls
            .SIDE_ALIGNMENT_MINIMUM_GAP_DIFFERENCE_RATIO
        )

        maximum_side_edge_variance = max(
            edge_tolerance,
            reference_width
            * cls
            .SIDE_ALIGNMENT_MAXIMUM_EDGE_VARIANCE_RATIO,
        )

        right_aligned = (
            result.right_gap
            <= side_gap_tolerance
            and (
                result.left_gap
                - result.right_gap
            )
            >= minimum_gap_difference
            and result.right_edge_variance
            <= maximum_side_edge_variance
        )

        if right_aligned:
            result.alignment = (
                ParagraphAlignment.RIGHT
            )

            right_anchor_score = max(
                0.0,
                1.0
                - (
                    result.right_gap
                    / max(
                        side_gap_tolerance,
                        1.0,
                    )
                ),
            )

            edge_score = max(
                0.0,
                1.0
                - (
                    result.right_edge_variance
                    / max(
                        maximum_side_edge_variance,
                        1.0,
                    )
                ),
            )

            result.set_confidence(
                (
                    0.55
                    + right_anchor_score * 0.25
                    + edge_score * 0.20
                )
            )

            result.add_reason(
                (
                    "Visible line-right edges are stable "
                    "and close to the container's right "
                    "edge."
                )
            )

            return result

        # -----------------------------------------------------
        # 5. Left-aligned
        # -----------------------------------------------------

        left_aligned = (
            result.left_gap
            <= side_gap_tolerance * 1.5
            or result.left_edge_variance
            <= maximum_side_edge_variance
        )

        if left_aligned:
            result.alignment = (
                ParagraphAlignment.LEFT
            )

            left_anchor_score = max(
                0.0,
                1.0
                - (
                    result.left_gap
                    / max(
                        side_gap_tolerance * 1.5,
                        1.0,
                    )
                ),
            )

            edge_score = max(
                0.0,
                1.0
                - (
                    result.left_edge_variance
                    / max(
                        maximum_side_edge_variance,
                        1.0,
                    )
                ),
            )

            result.set_confidence(
                (
                    0.50
                    + left_anchor_score * 0.25
                    + edge_score * 0.20
                )
            )

            result.add_reason(
                (
                    "Visible line-left edges are stable "
                    "or close to the container's left "
                    "edge."
                )
            )

            return result

        # -----------------------------------------------------
        # 6. Unknown
        # -----------------------------------------------------

        result.alignment = (
            ParagraphAlignment.UNKNOWN
        )

        result.set_confidence(
            0.30
        )

        result.add_warning(
            (
                "Paragraph geometry does not provide "
                "enough evidence for reliable alignment."
            )
        )

        return result

    # ---------------------------------------------------------
    # Justified-text detection
    # ---------------------------------------------------------

    @classmethod
    def _looks_justified(
        cls,
        result: ParagraphAlignmentResult,
        line_geometries: list[_LineGeometry],
        reference_width: float,
        edge_tolerance: float,
        side_gap_tolerance: float,
    ) -> bool:
        if (
            len(line_geometries)
            < cls.JUSTIFY_MINIMUM_LINE_COUNT
        ):
            return False

        nonfinal_lines = (
            line_geometries[:-1]
        )

        if not nonfinal_lines:
            return False

        nonfinal_left_variance = (
            cls._standard_deviation([
                line.left
                for line in nonfinal_lines
            ])
        )

        nonfinal_right_variance = (
            cls._standard_deviation([
                line.right
                for line in nonfinal_lines
            ])
        )

        nonfinal_width_ratio = (
            median([
                line.width
                for line in nonfinal_lines
            ])
            / max(
                reference_width,
                1.0,
            )
        )

        maximum_edge_variance = max(
            edge_tolerance,
            reference_width
            * cls
            .JUSTIFY_MAXIMUM_EDGE_VARIANCE_RATIO,
        )

        stable_nonfinal_edges = (
            nonfinal_left_variance
            <= maximum_edge_variance
            and nonfinal_right_variance
            <= maximum_edge_variance
        )

        nonfinal_lines_are_wide = (
            nonfinal_width_ratio
            >= cls
            .JUSTIFY_MINIMUM_NONFINAL_WIDTH_RATIO
        )

        final_line_is_shorter = (
            result.last_line_width_ratio
            <= cls
            .JUSTIFY_MAXIMUM_LAST_LINE_REFERENCE_RATIO
            and result.last_line_relative_width
            <= cls
            .JUSTIFY_MAXIMUM_LAST_LINE_RELATIVE_RATIO
        )

        paragraph_near_container_edges = (
            result.left_gap
            <= side_gap_tolerance * 2.0
            and result.right_gap
            <= side_gap_tolerance * 2.0
        )

        return (
            stable_nonfinal_edges
            and nonfinal_lines_are_wide
            and final_line_is_shorter
            and paragraph_near_container_edges
        )

    @classmethod
    def _justify_confidence(
        cls,
        result: ParagraphAlignmentResult,
        reference_width: float,
    ) -> float:
        left_edge_score = max(
            0.0,
            1.0
            - (
                result.left_edge_variance
                / max(
                    reference_width * 0.04,
                    1.0,
                )
            ),
        )

        right_edge_score = max(
            0.0,
            1.0
            - (
                result.right_edge_variance
                / max(
                    reference_width * 0.04,
                    1.0,
                )
            ),
        )

        final_line_score = max(
            0.0,
            1.0
            - result.last_line_relative_width,
        )

        confidence = (
            0.55
            + left_edge_score * 0.15
            + right_edge_score * 0.15
            + final_line_score * 0.15
        )

        if result.line_count == 2:
            confidence -= 0.05

        return cls._clamp(
            confidence
        )

    # ---------------------------------------------------------
    # Container resolution
    # ---------------------------------------------------------

    @classmethod
    def _resolve_reference_container(
        cls,
        page: Page,
        paragraph: Any,
        paragraph_region_number: int,
        paragraph_bbox: Bounds,
    ) -> tuple[
        AlignmentReferenceType,
        int | None,
        Bounds,
    ]:
        page_bbox = (
            RectangleUnion
            .normalize_rectangle(
                page.bbox
            )
        )

        if page_bbox is None:
            page_bbox = paragraph_bbox

        columns = list(
            getattr(
                page,
                "column_regions",
                [],
            )
            or []
        )

        layout_regions = list(
            getattr(
                page,
                "layout_regions",
                [],
            )
            or []
        )

        column_by_id = {
            column.column_id: column
            for column in columns
        }

        layout_region_by_id = {
            region.region_id: region
            for region in layout_regions
        }

        is_multi_column_page = (
            len(columns) >= 2
        )

        explicit_column_id = getattr(
            paragraph,
            "column_id",
            None,
        )

        # A real multi-column page should use its individual
        # column as the alignment reference.
        if (
            is_multi_column_page
            and explicit_column_id
            in column_by_id
        ):
            column = column_by_id[
                explicit_column_id
            ]

            column_bbox = (
                RectangleUnion
                .normalize_rectangle(
                    column.bbox
                )
            )

            if column_bbox is not None:
                return (
                    AlignmentReferenceType.COLUMN,
                    column.column_id,
                    column_bbox,
                )

        # Recover column membership even when paragraph
        # metadata has not yet been attached.
        if is_multi_column_page:
            for column in columns:
                if (
                    paragraph_region_number
                    in column.paragraph_region_numbers
                ):
                    column_bbox = (
                        RectangleUnion
                        .normalize_rectangle(
                            column.bbox
                        )
                    )

                    if column_bbox is not None:
                        return (
                            AlignmentReferenceType.COLUMN,
                            column.column_id,
                            column_bbox,
                        )

        explicit_layout_region_id = getattr(
            paragraph,
            "layout_region_id",
            None,
        )

        if (
            explicit_layout_region_id
            in layout_region_by_id
        ):
            region = layout_region_by_id[
                explicit_layout_region_id
            ]

            return cls._reference_from_layout_region(
                page_bbox=page_bbox,
                region=region,
                layout_region_by_id=(
                    layout_region_by_id
                ),
                column_count=len(
                    columns
                ),
            )

        # Recover layout-region membership from the region's
        # paragraph-number list.
        membership_regions = [
            region
            for region in layout_regions
            if (
                paragraph_region_number
                in region
                .paragraph_region_numbers
            )
        ]

        if membership_regions:
            membership_regions.sort(
                key=lambda region: (
                    cls._layout_region_priority(
                        region.region_type
                    ),
                    cls._region_area(
                        region
                    ),
                )
            )

            return cls._reference_from_layout_region(
                page_bbox=page_bbox,
                region=membership_regions[0],
                layout_region_by_id=(
                    layout_region_by_id
                ),
                column_count=len(
                    columns
                ),
            )

        # Last layout fallback: choose the smallest region
        # substantially overlapping the paragraph.
        overlapping_regions = []

        paragraph_area = (
            RectangleUnion.area(
                paragraph_bbox
            )
        )

        if paragraph_area > 0.0:
            for region in layout_regions:
                region_bbox = (
                    RectangleUnion
                    .normalize_rectangle(
                        region.bbox
                    )
                )

                if region_bbox is None:
                    continue

                intersection = (
                    RectangleUnion.intersection(
                        paragraph_bbox,
                        region_bbox,
                    )
                )

                overlap_ratio = (
                    RectangleUnion.area(
                        intersection
                    )
                    / paragraph_area
                    if intersection is not None
                    else 0.0
                )

                if (
                    overlap_ratio
                    >= cls
                    .MINIMUM_REGION_OVERLAP_RATIO
                ):
                    overlapping_regions.append(
                        region
                    )

        if overlapping_regions:
            overlapping_regions.sort(
                key=lambda region: (
                    cls._layout_region_priority(
                        region.region_type
                    ),
                    cls._region_area(
                        region
                    ),
                )
            )

            return cls._reference_from_layout_region(
                page_bbox=page_bbox,
                region=overlapping_regions[0],
                layout_region_by_id=(
                    layout_region_by_id
                ),
                column_count=len(
                    columns
                ),
            )

        return (
            AlignmentReferenceType.PAGE,
            None,
            page_bbox,
        )

    @classmethod
    def _reference_from_layout_region(
        cls,
        page_bbox: Bounds,
        region: LayoutRegion,
        layout_region_by_id: dict[
            int,
            LayoutRegion,
        ],
        column_count: int,
    ) -> tuple[
        AlignmentReferenceType,
        int | None,
        Bounds,
    ]:
        region_bbox = (
            RectangleUnion
            .normalize_rectangle(
                region.bbox
            )
        )

        if region_bbox is None:
            return (
                AlignmentReferenceType.PAGE,
                None,
                page_bbox,
            )

        if (
            region.region_type
            == LayoutRegionType.HEADER
        ):
            return (
                AlignmentReferenceType.HEADER,
                region.region_id,
                cls._expand_band_to_page_width(
                    page_bbox=page_bbox,
                    region_bbox=region_bbox,
                ),
            )

        if (
            region.region_type
            == LayoutRegionType.FOOTER
        ):
            return (
                AlignmentReferenceType.FOOTER,
                region.region_id,
                cls._expand_band_to_page_width(
                    page_bbox=page_bbox,
                    region_bbox=region_bbox,
                ),
            )

        if (
            region.region_type
            == LayoutRegionType.PAGE_BODY
        ):
            return (
                AlignmentReferenceType.PAGE_BODY,
                region.region_id,
                region_bbox,
            )

        if (
            region.region_type
            == LayoutRegionType.COLUMN
            and column_count <= 1
        ):
            # One detected column normally represents the
            # page body rather than a true multi-column
            # structure. Use its parent body container when
            # possible.
            parent_region = (
                layout_region_by_id.get(
                    region.parent_region_id
                )
            )

            if (
                parent_region is not None
                and parent_region.region_type
                == LayoutRegionType.PAGE_BODY
            ):
                parent_bbox = (
                    RectangleUnion
                    .normalize_rectangle(
                        parent_region.bbox
                    )
                )

                if parent_bbox is not None:
                    return (
                        AlignmentReferenceType.PAGE_BODY,
                        parent_region.region_id,
                        parent_bbox,
                    )

        return (
            AlignmentReferenceType.LAYOUT_REGION,
            region.region_id,
            region_bbox,
        )

    @staticmethod
    def _expand_band_to_page_width(
        page_bbox: Bounds,
        region_bbox: Bounds,
    ) -> Bounds:
        """
        Header/footer regions are detected from their content,
        so their horizontal bounds may be very narrow.

        Alignment inside a header/footer must instead be
        measured against the full page band.
        """

        return (
            page_bbox[0],
            region_bbox[1],
            page_bbox[2],
            region_bbox[3],
        )

    @staticmethod
    def _layout_region_priority(
        region_type: LayoutRegionType,
    ) -> int:
        priority_map = {
            LayoutRegionType.HEADER: 0,
            LayoutRegionType.FOOTER: 0,
            LayoutRegionType.COLUMN: 1,
            LayoutRegionType.PAGE_BODY: 2,
            LayoutRegionType.SIDEBAR: 3,
            LayoutRegionType.TITLE_AREA: 3,
            LayoutRegionType.TEXT_AREA: 3,
            LayoutRegionType.TABLE_AREA: 3,
            LayoutRegionType.FIGURE_AREA: 3,
            LayoutRegionType.CHART_AREA: 3,
            LayoutRegionType.FORM_AREA: 3,
            LayoutRegionType.DECORATIVE_AREA: 4,
            LayoutRegionType.UNKNOWN: 5,
        }

        return priority_map.get(
            region_type,
            5,
        )

    @staticmethod
    def _region_area(
        region: LayoutRegion,
    ) -> float:
        return max(
            region.width
            * region.height,
            0.0,
        )

    # ---------------------------------------------------------
    # Line collection
    # ---------------------------------------------------------

    @classmethod
    def _collect_line_geometries(
        cls,
        paragraph: Any,
        paragraph_bbox: Bounds,
    ) -> list[_LineGeometry]:
        geometries: list[
            _LineGeometry
        ] = []

        for line in getattr(
            paragraph,
            "lines",
            [],
        ) or []:
            text = cls._extract_line_text(
                line
            )

            if not text:
                continue

            line_bbox = (
                RectangleUnion
                .normalize_rectangle(
                    line
                )
            )

            if line_bbox is None:
                line_bbox = (
                    cls._bbox_from_spans(
                        getattr(
                            line,
                            "spans",
                            [],
                        )
                        or []
                    )
                )

            if line_bbox is None:
                continue

            geometries.append(
                _LineGeometry(
                    text=text,
                    bbox=line_bbox,
                )
            )

        if not geometries:
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            geometries.append(
                _LineGeometry(
                    text=text,
                    bbox=paragraph_bbox,
                )
            )

        geometries.sort(
            key=lambda line: (
                line.top,
                line.left,
                line.bottom,
            )
        )

        return geometries

    @staticmethod
    def _extract_line_text(
        line: Any,
    ) -> str:
        direct_text = str(
            getattr(
                line,
                "text",
                "",
            )
        ).strip()

        if direct_text:
            return direct_text

        text_parts: list[str] = []

        for span in getattr(
            line,
            "spans",
            [],
        ) or []:
            span_text = str(
                getattr(
                    span,
                    "text",
                    "",
                )
            ).strip()

            if span_text:
                text_parts.append(
                    span_text
                )

        return " ".join(
            text_parts
        )

    @staticmethod
    def _bbox_from_spans(
        spans: Iterable[Any],
    ) -> Bounds | None:
        bounds = [
            normalized
            for span in spans
            if (
                normalized := (
                    RectangleUnion
                    .normalize_rectangle(
                        span
                    )
                )
            ) is not None
        ]

        if not bounds:
            return None

        return (
            min(
                bbox[0]
                for bbox in bounds
            ),
            min(
                bbox[1]
                for bbox in bounds
            ),
            max(
                bbox[2]
                for bbox in bounds
            ),
            max(
                bbox[3]
                for bbox in bounds
            ),
        )

    @classmethod
    def _resolve_paragraph_bbox(
        cls,
        paragraph: Any,
    ) -> Bounds | None:
        paragraph_bbox = (
            RectangleUnion
            .normalize_rectangle(
                paragraph
            )
        )

        if paragraph_bbox is not None:
            return paragraph_bbox

        line_bounds: list[Bounds] = []

        for line in getattr(
            paragraph,
            "lines",
            [],
        ) or []:
            line_bbox = (
                RectangleUnion
                .normalize_rectangle(
                    line
                )
            )

            if line_bbox is None:
                line_bbox = (
                    cls._bbox_from_spans(
                        getattr(
                            line,
                            "spans",
                            [],
                        )
                        or []
                    )
                )

            if line_bbox is not None:
                line_bounds.append(
                    line_bbox
                )

        if not line_bounds:
            return None

        return (
            min(
                bbox[0]
                for bbox in line_bounds
            ),
            min(
                bbox[1]
                for bbox in line_bounds
            ),
            max(
                bbox[2]
                for bbox in line_bounds
            ),
            max(
                bbox[3]
                for bbox in line_bounds
            ),
        )

    # ---------------------------------------------------------
    # Indentation and list detection
    # ---------------------------------------------------------

    @classmethod
    def _detect_hanging_indent(
        cls,
        paragraph: Any,
        lines: list[_LineGeometry],
        reference_left: float,
        reference_width: float,
    ) -> bool:
        """
        Detect a genuine hanging indent.
    
        Explicit list-marker geometry is considered the strongest
        evidence.
    
        Line-based indentation is accepted only when the first
        line begins near the left edge of the containing region.
        This prevents right-aligned paragraphs from being
        mistaken for hanging indents merely because shorter lines
        start farther to the right.
        """
    
        indentation_threshold = max(
            cls.MINIMUM_HANGING_INDENT,
            reference_width
            * cls.HANGING_INDENT_RATIO,
        )
    
        # ---------------------------------------------------------
        # Strong evidence: explicit list-marker geometry
        # ---------------------------------------------------------
    
        list_marker_left = getattr(
            paragraph,
            "list_marker_left",
            None,
        )
    
        content_left = getattr(
            paragraph,
            "content_left",
            None,
        )
    
        try:
            if (
                list_marker_left is not None
                and content_left is not None
                and (
                    float(content_left)
                    - float(list_marker_left)
                )
                >= indentation_threshold
            ):
                return True
    
        except (
            TypeError,
            ValueError,
        ):
            pass
        
        # At least two lines are required for a geometric hanging
        # indent.
        if len(lines) < 2:
            return False
    
        first_line_left = (
            lines[0].left
        )
    
        remaining_lines_left = median([
            line.left
            for line in lines[1:]
        ])
    
        indentation_amount = (
            remaining_lines_left
            - first_line_left
        )
    
        if (
            indentation_amount
            < indentation_threshold
        ):
            return False
    
        # A hanging indent normally starts near the left edge of
        # its containing column/body region.
        #
        # A right-aligned paragraph may also have later lines
        # starting farther right, but its first line is normally
        # far from the container's left edge.
        left_anchor_tolerance = max(
            indentation_threshold * 1.50,
            reference_width * 0.06,
        )
    
        first_line_left_gap = max(
            first_line_left
            - reference_left,
            0.0,
        )
    
        if (
            first_line_left_gap
            > left_anchor_tolerance
        ):
            return False
    
        return True

    @staticmethod
    def _is_list_paragraph(
        paragraph: Any,
    ) -> bool:
        list_type = getattr(
            paragraph,
            "list_type",
            None,
        )

        list_marker = getattr(
            paragraph,
            "list_marker",
            None,
        )

        return bool(
            list_type
            or (
                list_marker is not None
                and str(
                    list_marker
                ).strip()
            )
        )

    # ---------------------------------------------------------
    # Result assignment
    # ---------------------------------------------------------

    @staticmethod
    def _assign_result_to_paragraph(
        paragraph: Any,
        result: ParagraphAlignmentResult,
    ) -> None:
        setattr(
            paragraph,
            "detected_alignment",
            result.alignment,
        )

        setattr(
            paragraph,
            "alignment_confidence",
            result.confidence,
        )

        setattr(
            paragraph,
            "alignment_reference_type",
            result.reference_type,
        )

        setattr(
            paragraph,
            "alignment_reference_id",
            result.reference_id,
        )

    @staticmethod
    def _reset_paragraph_alignment(
        paragraph: Any,
    ) -> None:
        setattr(
            paragraph,
            "detected_alignment",
            ParagraphAlignment.UNKNOWN,
        )

        setattr(
            paragraph,
            "alignment_confidence",
            0.0,
        )

        setattr(
            paragraph,
            "alignment_reference_type",
            AlignmentReferenceType.UNKNOWN,
        )

        setattr(
            paragraph,
            "alignment_reference_id",
            None,
        )

    # ---------------------------------------------------------
    # Numeric helpers
    # ---------------------------------------------------------

    @staticmethod
    def _standard_deviation(
        values: Iterable[float],
    ) -> float:
        normalized_values = [
            float(value)
            for value in values
        ]

        if len(normalized_values) <= 1:
            return 0.0

        return float(
            pstdev(
                normalized_values
            )
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