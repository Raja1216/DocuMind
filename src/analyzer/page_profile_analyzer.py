from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from src.models.page import Page
from src.models.page_profile import (
    ConversionMode,
    PageProfile,
    PageType,
)
from src.utils.rectangle_union import (
    Bounds,
    RectangleUnion,
)


class PageProfileAnalyzer:
    """
    Calculates general page-level metrics and recommends a
    conversion strategy.

    This analyzer must not contain:

        filename-specific rules
        page-number-specific rules
        sample-PDF-specific rules
    """

    MINIMUM_VISIBLE_CHARACTERS = 3

    OCR_MINIMUM_IMAGE_COVERAGE = 0.50
    IMAGE_DOMINANT_COVERAGE = 0.60

    TABLE_DOMINANT_COVERAGE = 0.30
    CHART_DOMINANT_COVERAGE = 0.12

    COVER_MAXIMUM_TEXT_COVERAGE = 0.18
    COVER_MAXIMUM_PARAGRAPHS = 12

    COVER_MINIMUM_VISUAL_COVERAGE = 0.12
    COVER_MINIMUM_TITLE_SIZE = 24.0
    COVER_SPARSE_MAXIMUM_PARAGRAPHS = 4
    COVER_SPARSE_TITLE_SIZE_RATIO = 1.25

    COVER_NORMAL_TITLE_SIZE_RATIO = 1.80
    COVER_VERY_LARGE_TITLE_SIZE = 36.0

    MAGAZINE_MINIMUM_VISUAL_COVERAGE = 0.18

    COLUMN_MINIMUM_REGIONS = 4
    COLUMN_MINIMUM_TEXT_LENGTH = 20
    COLUMN_MAXIMUM_REGION_WIDTH_RATIO = 0.72
    COLUMN_MINIMUM_CENTER_GAP_RATIO = 0.14
    COLUMN_MINIMUM_VERTICAL_OVERLAP = 0.20

    CHART_GROUP_DISTANCE = 24.0

    IGNORED_VECTOR_CATEGORIES = {
        "background",
        "noise",
        "bullet",
        "separator",
    }

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> PageProfile:
        """
        Analyze one mapped and structurally processed page.
        """

        page_bounds = (
            RectangleUnion
            .normalize_rectangle(
                page.bbox
            )
        )

        if page_bounds is None:
            page_width = max(
                float(
                    getattr(
                        page.bbox,
                        "width",
                        0.0,
                    )
                ),
                0.0,
            )

            page_height = max(
                float(
                    getattr(
                        page.bbox,
                        "height",
                        0.0,
                    )
                ),
                0.0,
            )

            page_bounds = (
                0.0,
                0.0,
                page_width,
                page_height,
            )

        else:
            page_width = max(
                page_bounds[2]
                - page_bounds[0],
                0.0,
            )

            page_height = max(
                page_bounds[3]
                - page_bounds[1],
                0.0,
            )

        profile = PageProfile(
            page_number=page.number,
            page_width=page_width,
            page_height=page_height,
            rotation=(
                int(
                    getattr(
                        page,
                        "rotation",
                        0,
                    )
                )
                % 360
            ),
        )

        page.profile = profile

        text_rectangles = (
            cls._collect_text_rectangles(
                page
            )
        )

        image_rectangles = (
            cls._collect_element_rectangles(
                getattr(
                    page,
                    "images",
                    [],
                )
            )
        )

        vector_graphics = list(
            getattr(
                page,
                "vector_graphics",
                [],
            )
            or []
        )

        vector_rectangles = (
            cls._collect_vector_rectangles(
                vector_graphics
            )
        )

        chart_graphics = [
            graphic
            for graphic in vector_graphics
            if (
                cls._category_name(
                    getattr(
                        graphic,
                        "category",
                        None,
                    )
                )
                == "chart"
            )
        ]

        chart_rectangles = (
            cls._collect_element_rectangles(
                chart_graphics
            )
        )

        tables = list(
            getattr(
                page,
                "tables",
                [],
            )
            or []
        )

        table_rectangles = (
            cls._collect_element_rectangles(
                tables
            )
        )

        profile.text_coverage = (
            RectangleUnion.coverage(
                rectangles=text_rectangles,
                container=page_bounds,
            )
        )

        profile.image_coverage = (
            RectangleUnion.coverage(
                rectangles=image_rectangles,
                container=page_bounds,
            )
        )

        profile.vector_coverage = (
            RectangleUnion.coverage(
                rectangles=vector_rectangles,
                container=page_bounds,
            )
        )

        profile.table_coverage = (
            RectangleUnion.coverage(
                rectangles=table_rectangles,
                container=page_bounds,
            )
        )

        profile.chart_coverage = (
            RectangleUnion.coverage(
                rectangles=chart_rectangles,
                container=page_bounds,
            )
        )

        (
            profile.text_block_count,
            visible_character_count,
        ) = cls._text_statistics(
            page
        )

        profile.paragraph_count = len([
            region
            for region in getattr(
                page,
                "paragraph_regions",
                [],
            )
            if str(
                getattr(
                    region,
                    "text",
                    "",
                )
            ).strip()
        ])

        profile.image_count = len(
            getattr(
                page,
                "images",
                [],
            )
            or []
        )

        profile.vector_count = len(
            vector_graphics
        )

        profile.vector_region_count = len(
            getattr(
                page,
                "vector_regions",
                [],
            )
            or []
        )

        profile.table_count = len(
            tables
        )

        profile.chart_count = (
            cls._count_chart_groups(
                chart_graphics
            )
        )

        profile.form_field_count = (
            cls._count_form_fields(
                page
            )
        )

        profile.has_extractable_text = (
            visible_character_count
            >= cls.MINIMUM_VISIBLE_CHARACTERS
        )

        profile.requires_ocr = (
            not profile.has_extractable_text
            and profile.image_count > 0
            and profile.image_coverage
            >= cls.OCR_MINIMUM_IMAGE_COVERAGE
        )

        profile.column_count = (
            cls._estimate_column_count(
                page=page,
                page_bounds=page_bounds,
            )
        )

        (
            maximum_font_size,
            median_font_size,
        ) = cls._font_statistics(
            page
        )

        profile.page_type = (
            cls._classify_page(
                profile=profile,
                maximum_font_size=(
                    maximum_font_size
                ),
                median_font_size=(
                    median_font_size
                ),
            )
        )

        cls._calculate_confidences(
            profile
        )

        cls._resolve_conversion_mode(
            profile
        )

        cls._add_profile_explanations(
            profile=profile,
            maximum_font_size=(
                maximum_font_size
            ),
            median_font_size=(
                median_font_size
            ),
        )

        return profile

    @classmethod
    def _collect_text_rectangles(
        cls,
        page: Page,
    ) -> list[Bounds]:
        """
        Collect visible span rectangles.

        Span rectangles are preferred over block rectangles
        because blocks may contain large blank areas.
        """

        rectangles: list[Bounds] = []

        for block in getattr(
            page,
            "blocks",
            [],
        ):
            for line in getattr(
                block,
                "lines",
                [],
            ):
                for span in getattr(
                    line,
                    "spans",
                    [],
                ):
                    if not str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                    ).strip():
                        continue

                    bounds = (
                        RectangleUnion
                        .normalize_rectangle(
                            span
                        )
                    )

                    if bounds is not None:
                        rectangles.append(
                            bounds
                        )

        if rectangles:
            return rectangles

        # Fallback for models that contain paragraph regions
        # but no original block/span hierarchy.
        return cls._collect_element_rectangles(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
        )

    @classmethod
    def _collect_vector_rectangles(
        cls,
        vector_graphics: Iterable[Any],
    ) -> list[Bounds]:
        rectangles: list[Bounds] = []

        for graphic in vector_graphics:
            category = cls._category_name(
                getattr(
                    graphic,
                    "category",
                    None,
                )
            )

            if (
                category
                in cls.IGNORED_VECTOR_CATEGORIES
            ):
                continue

            bounds = (
                RectangleUnion
                .normalize_rectangle(
                    graphic
                )
            )

            if bounds is not None:
                rectangles.append(
                    bounds
                )

        return rectangles

    @staticmethod
    def _collect_element_rectangles(
        elements: Iterable[Any],
    ) -> list[Bounds]:
        rectangles: list[Bounds] = []

        for element in elements:
            bounds = (
                RectangleUnion
                .normalize_rectangle(
                    element
                )
            )

            if bounds is not None:
                rectangles.append(
                    bounds
                )

        return rectangles

    @classmethod
    def _text_statistics(
        cls,
        page: Page,
    ) -> tuple[int, int]:
        """
        Return:

            visible text-block count,
            visible character count
        """

        visible_block_count = 0
        visible_character_count = 0

        for block in getattr(
            page,
            "blocks",
            [],
        ):
            block_has_text = False

            for line in getattr(
                block,
                "lines",
                [],
            ):
                for span in getattr(
                    line,
                    "spans",
                    [],
                ):
                    text = str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                    )

                    stripped_text = (
                        text.strip()
                    )

                    if not stripped_text:
                        continue

                    block_has_text = True

                    visible_character_count += len(
                        stripped_text
                    )

            if block_has_text:
                visible_block_count += 1

        return (
            visible_block_count,
            visible_character_count,
        )

    @classmethod
    def _font_statistics(
        cls,
        page: Page,
    ) -> tuple[float, float]:
        font_sizes: list[float] = []

        for block in getattr(
            page,
            "blocks",
            [],
        ):
            for line in getattr(
                block,
                "lines",
                [],
            ):
                for span in getattr(
                    line,
                    "spans",
                    [],
                ):
                    if not str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                    ).strip():
                        continue

                    try:
                        font_size = float(
                            getattr(
                                span,
                                "font_size",
                                0.0,
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    if font_size > 0.0:
                        font_sizes.append(
                            font_size
                        )

        if not font_sizes:
            return (
                0.0,
                0.0,
            )

        return (
            max(font_sizes),
            float(
                median(
                    font_sizes
                )
            ),
        )

    @classmethod
    def _classify_page(
        cls,
        profile: PageProfile,
        maximum_font_size: float,
        median_font_size: float,
    ) -> PageType:
        """
        Assign one high-level page type using general content
        evidence.
        """

        if profile.form_field_count > 0:
            return PageType.FORM

        if profile.requires_ocr:
            return PageType.SCANNED

        if cls._looks_like_designed_cover(
            profile=profile,
            maximum_font_size=(
                maximum_font_size
            ),
            median_font_size=(
                median_font_size
            ),
        ):
            return PageType.DESIGNED_COVER

        if (
            profile.table_count > 0
            and (
                profile.table_coverage
                >= cls.TABLE_DOMINANT_COVERAGE
                or profile.table_coverage
                >= max(
                    profile.text_coverage,
                    0.18,
                )
            )
        ):
            return PageType.TABLE_DOMINANT

        if (
            profile.chart_count > 0
            and (
                profile.chart_coverage
                >= cls.CHART_DOMINANT_COVERAGE
                or profile.chart_coverage
                >= profile.text_coverage
            )
        ):
            return PageType.CHART_DOMINANT

        combined_visual_coverage = (
            profile.image_coverage
            + profile.vector_coverage
        )

        if (
            profile.column_count >= 2
            and combined_visual_coverage
            >= cls.MAGAZINE_MINIMUM_VISUAL_COVERAGE
            and profile.text_coverage > 0.02
        ):
            return PageType.MAGAZINE

        if (
            profile.image_coverage
            >= cls.IMAGE_DOMINANT_COVERAGE
            and profile.text_coverage < 0.12
        ):
            return PageType.IMAGE_DOMINANT

        if profile.column_count >= 2:
            return PageType.MULTI_COLUMN

        major_content_types = sum([
            profile.image_coverage >= 0.20,
            profile.vector_coverage >= 0.15,
            profile.table_coverage >= 0.15,
            profile.chart_coverage >= 0.10,
        ])

        if (
            profile.has_extractable_text
            and major_content_types >= 2
        ):
            return PageType.MIXED

        if profile.has_extractable_text:
            return PageType.SIMPLE_TEXT

        if (
            profile.image_count > 0
            or profile.vector_count > 0
        ):
            return PageType.IMAGE_DOMINANT

        return PageType.UNKNOWN

    @classmethod
    def _looks_like_designed_cover(
        cls,
        profile: PageProfile,
        maximum_font_size: float,
        median_font_size: float,
    ) -> bool:
        """
        Detect a designed cover or title page using multiple
        independent signals.
    
        This method does not depend on the page number. A cover or
        section-title page may occur anywhere in a document.
        """
    
        if not profile.has_extractable_text:
            return False
    
        if (
            profile.text_coverage
            > cls.COVER_MAXIMUM_TEXT_COVERAGE
        ):
            return False
    
        if (
            profile.paragraph_count
            > cls.COVER_MAXIMUM_PARAGRAPHS
        ):
            return False
    
        visual_coverage = min(
            profile.image_coverage
            + profile.vector_coverage,
            1.0,
        )
    
        has_visual_design = (
            visual_coverage
            >= cls.COVER_MINIMUM_VISUAL_COVERAGE
        )
    
        has_absolute_title_size = (
            maximum_font_size
            >= cls.COVER_MINIMUM_TITLE_SIZE
        )
    
        is_sparse_page = (
            profile.paragraph_count
            <= cls.COVER_SPARSE_MAXIMUM_PARAGRAPHS
        )
    
        if median_font_size > 0.0:
            title_size_ratio = (
                maximum_font_size
                / median_font_size
            )
        else:
            title_size_ratio = 0.0
    
        required_title_ratio = (
            cls.COVER_SPARSE_TITLE_SIZE_RATIO
            if is_sparse_page
            else cls.COVER_NORMAL_TITLE_SIZE_RATIO
        )
    
        has_prominent_title = (
            has_absolute_title_size
            and title_size_ratio
            >= required_title_ratio
        )
    
        has_very_large_sparse_title = (
            is_sparse_page
            and maximum_font_size
            >= cls.COVER_VERY_LARGE_TITLE_SIZE
        )
    
        # A visually designed, sparse page with a prominent or
        # very large title is likely a cover/title page.
        if (
            has_visual_design
            and (
                has_prominent_title
                or has_very_large_sparse_title
            )
        ):
            return True
    
        # Support sparse title pages with little or no decoration.
        # Require stronger typography evidence here to avoid
        # classifying ordinary short pages as covers.
        sparse_typographic_title_page = (
            is_sparse_page
            and profile.text_coverage <= 0.08
            and maximum_font_size
            >= cls.COVER_VERY_LARGE_TITLE_SIZE
            and (
                median_font_size <= 0.0
                or title_size_ratio >= 1.50
            )
        )
    
        return sparse_typographic_title_page

    @classmethod
    def _calculate_confidences(
        cls,
        profile: PageProfile,
    ) -> None:
        """
        Calculate initial conversion-confidence scores.

        These are heuristic baseline scores. They will later
        be calibrated using the reference corpus.
        """

        editable_score = (
            0.15
            + (
                0.25
                if profile.has_extractable_text
                else 0.0
            )
            + min(
                profile.text_coverage
                * 1.50,
                0.40,
            )
            - min(
                profile.image_coverage
                * 0.40,
                0.30,
            )
            - min(
                profile.vector_coverage
                * 0.20,
                0.20,
            )
        )

        if profile.column_count >= 2:
            editable_score -= 0.10

        if profile.page_type in {
            PageType.DESIGNED_COVER,
            PageType.MAGAZINE,
            PageType.SCANNED,
            PageType.IMAGE_DOMINANT,
        }:
            editable_score -= 0.20

        if profile.requires_ocr:
            editable_score = 0.05

        fixed_score = (
            0.15
            + min(
                profile.image_coverage
                * 0.70,
                0.50,
            )
            + min(
                profile.vector_coverage
                * 0.60,
                0.40,
            )
        )

        if profile.page_type in {
            PageType.DESIGNED_COVER,
            PageType.MAGAZINE,
            PageType.IMAGE_DOMINANT,
        }:
            fixed_score += 0.20

        if profile.requires_ocr:
            fixed_score += 0.15

        structural_complexity_bonus = 0.0

        if profile.table_count > 0:
            structural_complexity_bonus += 0.10

        if profile.chart_count > 0:
            structural_complexity_bonus += 0.15

        if profile.column_count >= 2:
            structural_complexity_bonus += 0.10

        if profile.form_field_count > 0:
            structural_complexity_bonus += 0.15

        hybrid_score = (
            max(
                editable_score,
                fixed_score,
            )
            * 0.70
            + min(
                editable_score,
                fixed_score,
            )
            * 0.30
            + structural_complexity_bonus
        )

        ocr_score = 0.0

        if profile.requires_ocr:
            ocr_score = max(
                0.85,
                profile.image_coverage,
            )

        elif (
            not profile.has_extractable_text
            and profile.image_count > 0
        ):
            ocr_score = min(
                profile.image_coverage,
                0.75,
            )

        profile.editable_confidence = (
            RectangleUnion.clamp_ratio(
                editable_score
            )
        )

        profile.fixed_confidence = (
            RectangleUnion.clamp_ratio(
                fixed_score
            )
        )

        profile.hybrid_confidence = (
            RectangleUnion.clamp_ratio(
                hybrid_score
            )
        )

        profile.ocr_confidence = (
            RectangleUnion.clamp_ratio(
                ocr_score
            )
        )

    @staticmethod
    def _resolve_conversion_mode(
        profile: PageProfile,
    ) -> None:
        """
        Select the initial recommended mode for the page.
        """

        mode_map = {
            PageType.SIMPLE_TEXT: (
                ConversionMode.EDITABLE
            ),

            PageType.MULTI_COLUMN: (
                ConversionMode.HYBRID
            ),

            PageType.DESIGNED_COVER: (
                ConversionMode.HYBRID
            ),

            PageType.TABLE_DOMINANT: (
                ConversionMode.HYBRID
            ),

            PageType.CHART_DOMINANT: (
                ConversionMode.HYBRID
            ),

            PageType.FORM: (
                ConversionMode.HYBRID
            ),

            PageType.IMAGE_DOMINANT: (
                ConversionMode.FIXED
            ),

            PageType.SCANNED: (
                ConversionMode.OCR
            ),

            PageType.MAGAZINE: (
                ConversionMode.HYBRID
            ),

            PageType.MIXED: (
                ConversionMode.HYBRID
            ),

            PageType.UNKNOWN: (
                ConversionMode.HYBRID
            ),
        }

        profile.recommended_mode = (
            mode_map[
                profile.page_type
            ]
        )

    @classmethod
    def _add_profile_explanations(
        cls,
        profile: PageProfile,
        maximum_font_size: float,
        median_font_size: float,
    ) -> None:
        profile.add_reason(
            (
                f"Page classified as "
                f"{profile.page_type.value}."
            )
        )

        profile.add_reason(
            (
                f"Text coverage: "
                f"{profile.text_coverage:.3f}."
            )
        )

        profile.add_reason(
            (
                f"Image coverage: "
                f"{profile.image_coverage:.3f}."
            )
        )

        profile.add_reason(
            (
                f"Vector coverage: "
                f"{profile.vector_coverage:.3f}."
            )
        )

        if profile.table_count > 0:
            profile.add_reason(
                (
                    f"Detected "
                    f"{profile.table_count} "
                    f"table region(s)."
                )
            )

        if profile.chart_count > 0:
            profile.add_reason(
                (
                    f"Detected "
                    f"{profile.chart_count} "
                    f"chart region(s)."
                )
            )

        if profile.column_count >= 2:
            profile.add_reason(
                (
                    "Provisional multi-column "
                    "layout evidence detected."
                )
            )

            profile.add_warning(
                (
                    "Column count is provisional until "
                    "the dedicated column engine runs."
                )
            )

        if profile.requires_ocr:
            profile.add_reason(
                (
                    "No reliable extractable text and "
                    "high image coverage."
                )
            )

            profile.add_warning(
                "OCR is required for this page."
            )

        if profile.chart_count > 0:
            profile.add_warning(
                (
                    "Chart conversion requires visual "
                    "fallback until the Chart Engine runs."
                )
            )

        if profile.form_field_count > 0:
            profile.add_warning(
                (
                    "Form controls require the dedicated "
                    "Form Engine."
                )
            )

        if (
            profile.page_type
            == PageType.DESIGNED_COVER
        ):
            profile.add_reason(
                (
                    f"Large-title evidence: "
                    f"max={maximum_font_size:.2f}, "
                    f"median={median_font_size:.2f}."
                )
            )

    @classmethod
    def _estimate_column_count(
        cls,
        page: Page,
        page_bounds: Bounds,
    ) -> int:
        """
        Return a conservative provisional column count.

        Full column detection is implemented later in
        Step 62.6G. This method only detects strong two-column
        evidence.
        """

        page_width = max(
            page_bounds[2]
            - page_bounds[0],
            1.0,
        )

        candidate_regions: list[
            tuple[
                Bounds,
                str,
            ]
        ] = []

        paragraph_regions = list(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        )

        source_elements: Iterable[Any] = (
            paragraph_regions
            if paragraph_regions
            else getattr(
                page,
                "blocks",
                [],
            )
        )

        for element in source_elements:
            text = str(
                getattr(
                    element,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                text = cls._element_text(
                    element
                )

            if (
                len(text)
                < cls.COLUMN_MINIMUM_TEXT_LENGTH
            ):
                continue

            bounds = (
                RectangleUnion
                .normalize_rectangle(
                    element
                )
            )

            if bounds is None:
                continue

            region_width = (
                bounds[2] - bounds[0]
            )

            if (
                region_width
                > page_width
                * cls.COLUMN_MAXIMUM_REGION_WIDTH_RATIO
            ):
                continue

            candidate_regions.append(
                (
                    bounds,
                    text,
                )
            )

        if (
            len(candidate_regions)
            < cls.COLUMN_MINIMUM_REGIONS
        ):
            return 1

        centered_regions = sorted(
            candidate_regions,
            key=lambda item: (
                item[0][0]
                + item[0][2]
            ) / 2.0,
        )

        centers = [
            (
                bounds[0]
                + bounds[2]
            ) / 2.0
            for bounds, _ in centered_regions
        ]

        gaps = [
            centers[index + 1]
            - centers[index]
            for index in range(
                len(centers) - 1
            )
        ]

        if not gaps:
            return 1

        largest_gap = max(gaps)

        split_index = (
            gaps.index(
                largest_gap
            )
            + 1
        )

        if (
            largest_gap
            < page_width
            * cls.COLUMN_MINIMUM_CENTER_GAP_RATIO
        ):
            return 1

        left_group = (
            centered_regions[
                :split_index
            ]
        )

        right_group = (
            centered_regions[
                split_index:
            ]
        )

        if (
            len(left_group) < 2
            or len(right_group) < 2
        ):
            return 1

        left_group_right_edge = median([
            bounds[2]
            for bounds, _ in left_group
        ])

        right_group_left_edge = median([
            bounds[0]
            for bounds, _ in right_group
        ])

        if (
            left_group_right_edge
            >= right_group_left_edge
        ):
            return 1

        left_top = min(
            bounds[1]
            for bounds, _ in left_group
        )

        left_bottom = max(
            bounds[3]
            for bounds, _ in left_group
        )

        right_top = min(
            bounds[1]
            for bounds, _ in right_group
        )

        right_bottom = max(
            bounds[3]
            for bounds, _ in right_group
        )

        vertical_overlap = max(
            min(
                left_bottom,
                right_bottom,
            )
            - max(
                left_top,
                right_top,
            ),
            0.0,
        )

        smaller_vertical_extent = max(
            min(
                left_bottom - left_top,
                right_bottom - right_top,
            ),
            1.0,
        )

        overlap_ratio = (
            vertical_overlap
            / smaller_vertical_extent
        )

        if (
            overlap_ratio
            < cls.COLUMN_MINIMUM_VERTICAL_OVERLAP
        ):
            return 1

        return 2

    @classmethod
    def _count_chart_groups(
        cls,
        chart_graphics: list[Any],
    ) -> int:
        """
        Count spatially separated chart-vector groups.
        """

        rectangles = [
            bounds
            for graphic in chart_graphics
            if (
                bounds := (
                    RectangleUnion
                    .normalize_rectangle(
                        graphic
                    )
                )
            ) is not None
        ]

        if not rectangles:
            return 0

        visited: set[int] = set()
        group_count = 0

        for index in range(
            len(rectangles)
        ):
            if index in visited:
                continue

            group_count += 1

            queue = [index]

            while queue:
                current_index = (
                    queue.pop()
                )

                if current_index in visited:
                    continue

                visited.add(
                    current_index
                )

                current_rectangle = (
                    rectangles[
                        current_index
                    ]
                )

                for other_index, other_rectangle in enumerate(
                    rectangles
                ):
                    if other_index in visited:
                        continue

                    if cls._rectangles_are_near(
                        current_rectangle,
                        other_rectangle,
                        cls.CHART_GROUP_DISTANCE,
                    ):
                        queue.append(
                            other_index
                        )

        return group_count

    @staticmethod
    def _rectangles_are_near(
        first: Bounds,
        second: Bounds,
        margin: float,
    ) -> bool:
        horizontal_gap = max(
            second[0] - first[2],
            first[0] - second[2],
            0.0,
        )

        vertical_gap = max(
            second[1] - first[3],
            first[1] - second[3],
            0.0,
        )

        return (
            horizontal_gap <= margin
            and vertical_gap <= margin
        )

    @staticmethod
    def _count_form_fields(
        page: Page,
    ) -> int:
        for attribute_name in (
            "form_fields",
            "widgets",
            "fields",
        ):
            value = getattr(
                page,
                attribute_name,
                None,
            )

            if value is None:
                continue

            try:
                return len(value)

            except TypeError:
                return sum(
                    1
                    for _ in value
                )

        return 0

    @staticmethod
    def _element_text(
        element: Any,
    ) -> str:
        text_parts: list[str] = []

        for line in getattr(
            element,
            "lines",
            [],
        ):
            for span in getattr(
                line,
                "spans",
                [],
            ):
                text = str(
                    getattr(
                        span,
                        "text",
                        "",
                    )
                ).strip()

                if text:
                    text_parts.append(
                        text
                    )

        return " ".join(
            text_parts
        )

    @staticmethod
    def _category_name(
        category: Any,
    ) -> str:
        if category is None:
            return ""

        if hasattr(
            category,
            "value",
        ):
            category = category.value

        return str(
            category
        ).strip().lower()