from __future__ import annotations

from src.models.vector_graphic import VectorGraphic


class VectorGraphicClassifier:
    """
    Classifies PDF vector drawings and determines whether
    they should remain in the general vector-graphics engine.
    """

    CATEGORY_BACKGROUND = "background"
    CATEGORY_DECORATIVE = "decorative"
    CATEGORY_BULLET = "bullet"
    CATEGORY_CHART = "chart"
    CATEGORY_SEPARATOR = "separator"
    CATEGORY_NOISE = "noise"
    CATEGORY_UNKNOWN = "unknown"

    PAGE_COVERAGE_THRESHOLD = 0.90

    BULLET_MAX_WIDTH = 12.0
    BULLET_MAX_HEIGHT = 12.0
    BULLET_MIN_WIDTH = 2.0
    BULLET_MIN_HEIGHT = 2.0

    NOISE_MAX_WIDTH = 1.0
    NOISE_MAX_HEIGHT = 1.0

    LONG_LINE_MIN_LENGTH = 80.0
    THIN_LINE_MAX_THICKNESS = 5.0

    CHART_MIN_COMPONENTS = 8
    CHART_CLUSTER_DISTANCE = 55.0
    
    CHART_PAGE_EDGE_MARGIN = 40.0
    CHART_MIN_CLUSTER_WIDTH = 120.0
    CHART_MIN_CLUSTER_HEIGHT = 70.0

    CHART_MAX_PAGE_COVERAGE = 0.70
    CHART_MIN_LONG_LINES = 2
    CHART_MIN_MARKERS_OR_BARS = 3

    @staticmethod
    def analyze_page(page) -> None:
        """
        Classify vector graphics in three passes.

        Pass 1:
        Remove definite backgrounds, decorative edge artwork,
        and tiny noise.

        Pass 2:
        Detect chart regions using all remaining drawings,
        including possible bullets and separator lines.

        Pass 3:
        Classify remaining non-chart drawings as bullets,
        separators, or unknown graphics.
        """

        graphics = page.vector_graphics

        if not graphics:
            return

        chart_candidates: list[VectorGraphic] = []

        # Pass 1: classify only graphics that are safe to identify
        # before chart-region analysis.
        for graphic in graphics:

            if VectorGraphicClassifier._is_page_background(
                page=page,
                graphic=graphic,
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_BACKGROUND
                )
                graphic.should_render = False
                continue

            if VectorGraphicClassifier._is_noise(
                graphic
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_NOISE
                )
                graphic.should_render = False
                continue

            if VectorGraphicClassifier._is_decorative(
                page=page,
                graphic=graphic,
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_DECORATIVE
                )
                graphic.should_render = True
                continue

            # Do not classify bullets or separators yet.
            # They may be chart markers or chart grid lines.
            graphic.category = (
                VectorGraphicClassifier
                .CATEGORY_UNKNOWN
            )
            graphic.should_render = True

            chart_candidates.append(
                graphic
            )

        # Pass 2: identify complete chart clusters.
        chart_graphics = (
            VectorGraphicClassifier
            ._detect_chart_components(
                page=page,
                graphics=chart_candidates,
            )
        )

        chart_ids = {
            id(graphic)
            for graphic in chart_graphics
        }

        # Pass 3: finalize all remaining objects.
        for graphic in chart_candidates:

            if id(graphic) in chart_ids:
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_CHART
                )
                graphic.should_render = False
                continue

            if VectorGraphicClassifier._is_bullet(
                graphic
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_BULLET
                )
                graphic.should_render = False
                continue

            if VectorGraphicClassifier._is_separator(
                graphic
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_SEPARATOR
                )
                graphic.should_render = True
                continue

            graphic.category = (
                VectorGraphicClassifier
                .CATEGORY_UNKNOWN
            )
            graphic.should_render = True

    @staticmethod
    def _classify_individual_graphic(
        page,
        graphic: VectorGraphic,
    ) -> str:

        if VectorGraphicClassifier._is_page_background(
            page=page,
            graphic=graphic,
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_BACKGROUND
            )

        if VectorGraphicClassifier._is_noise(
            graphic
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_NOISE
            )

        if VectorGraphicClassifier._is_bullet(
            graphic
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_BULLET
            )
            
        if VectorGraphicClassifier._is_decorative(
            page=page,
            graphic=graphic,
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_DECORATIVE
            )    

        if VectorGraphicClassifier._is_separator(
            graphic
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_SEPARATOR
            )

        return (
            VectorGraphicClassifier
            .CATEGORY_UNKNOWN
        )

    @staticmethod
    def _is_page_background(
        page,
        graphic: VectorGraphic,
    ) -> bool:
        """
        Detect a shape covering almost the complete page.
        """

        page_area = max(
            page.bbox.width
            * page.bbox.height,
            1.0,
        )

        coverage = (
            graphic.area / page_area
        )

        is_white = (
            graphic.fill_color
            in {
                "#FFFFFF",
                "#FEFEFE",
                "#FDFDFD",
            }
        )

        return (
            coverage
            >= VectorGraphicClassifier
            .PAGE_COVERAGE_THRESHOLD
            and is_white
        )

    @staticmethod
    def _is_noise(
        graphic: VectorGraphic,
    ) -> bool:
        return (
            graphic.width
            <= VectorGraphicClassifier
            .NOISE_MAX_WIDTH
            and graphic.height
            <= VectorGraphicClassifier
            .NOISE_MAX_HEIGHT
        )

    @staticmethod
    def _is_bullet(
        graphic: VectorGraphic,
    ) -> bool:
        """
        Detect small filled circular or curved bullet shapes.
        """

        if graphic.fill_color is None:
            return False

        return (
            VectorGraphicClassifier
            .BULLET_MIN_WIDTH
            <= graphic.width
            <= VectorGraphicClassifier
            .BULLET_MAX_WIDTH
            and
            VectorGraphicClassifier
            .BULLET_MIN_HEIGHT
            <= graphic.height
            <= VectorGraphicClassifier
            .BULLET_MAX_HEIGHT
            and graphic.drawing_type
            in {
                "curve",
                "compound",
            }
        )

    @staticmethod
    def _is_separator(
        graphic: VectorGraphic,
    ) -> bool:
        """
        Detect isolated long and thin divider lines.
        """

        is_horizontal = (
            graphic.width
            >= VectorGraphicClassifier
            .LONG_LINE_MIN_LENGTH
            and graphic.height
            <= VectorGraphicClassifier
            .THIN_LINE_MAX_THICKNESS
        )

        is_vertical = (
            graphic.height
            >= VectorGraphicClassifier
            .LONG_LINE_MIN_LENGTH
            and graphic.width
            <= VectorGraphicClassifier
            .THIN_LINE_MAX_THICKNESS
        )

        return (
            graphic.drawing_type == "line"
            and (
                is_horizontal
                or is_vertical
            )
        )

    @staticmethod
    def _is_decorative(
        page,
        graphic: VectorGraphic,
    ) -> bool:
        """
        Detect large colored artwork near or beyond page edges.

        This includes cover-page ribbons, footer shapes,
        background waves, and decorative corner graphics.
        """

        if graphic.fill_color is None:
            return False

        if graphic.fill_color in {
            "#FFFFFF",
            "#FEFEFE",
            "#FDFDFD",
        }:
            return False

        edge_margin = 30.0

        touches_or_exceeds_edge = any(
            (
                graphic.left <= edge_margin,
                graphic.top <= edge_margin,
                graphic.right
                >= page.bbox.width - edge_margin,
                graphic.bottom
                >= page.bbox.height - edge_margin,
                graphic.left < 0.0,
                graphic.top < 0.0,
                graphic.right > page.bbox.width,
                graphic.bottom > page.bbox.height,
            )
        )

        is_large = (
            graphic.width >= 25.0
            or graphic.height >= 25.0
        )

        return (
            touches_or_exceeds_edge
            and is_large
        )

    @staticmethod
    def _detect_chart_components(
        page,
        graphics: list[VectorGraphic],
    ) -> list[VectorGraphic]:
        """
        Detect dense groups of vector drawings that represent
        charts.

        Candidates may include:
        - grid lines;
        - axes;
        - bars;
        - line-series segments;
        - data-point markers;
        - legend symbols.
        """

        candidates = [
            graphic
            for graphic in graphics
            if (
                graphic.drawing_type
                in {
                    "line",
                    "curve",
                    "rectangle",
                    "compound",
                }
                and not (
                    VectorGraphicClassifier
                    ._touches_page_edge(
                        page=page,
                        graphic=graphic,
                    )
                )
            )
        ]

        if len(candidates) < (
            VectorGraphicClassifier
            .CHART_MIN_COMPONENTS
        ):
            return []

        clusters: list[
            list[VectorGraphic]
        ] = []

        for graphic in candidates:

            matching_clusters = []

            for cluster_index, cluster in enumerate(
                clusters
            ):
                if (
                    VectorGraphicClassifier
                    ._graphic_near_cluster(
                        graphic=graphic,
                        cluster=cluster,
                    )
                ):
                    matching_clusters.append(
                        cluster_index
                    )

            if not matching_clusters:
                clusters.append(
                    [graphic]
                )
                continue

            primary_index = matching_clusters[0]

            clusters[primary_index].append(
                graphic
            )

            # Merge clusters when the new graphic connects
            # multiple nearby groups.
            for merge_index in reversed(
                matching_clusters[1:]
            ):
                clusters[primary_index].extend(
                    clusters[merge_index]
                )

                del clusters[merge_index]

        chart_graphics: list[
            VectorGraphic
        ] = []

        for cluster in clusters:

            if len(cluster) < (
                VectorGraphicClassifier
                .CHART_MIN_COMPONENTS
            ):
                continue

            cluster_left = min(
                item.left
                for item in cluster
            )

            cluster_top = min(
                item.top
                for item in cluster
            )

            cluster_right = max(
                item.right
                for item in cluster
            )

            cluster_bottom = max(
                item.bottom
                for item in cluster
            )

            cluster_width = (
                cluster_right - cluster_left
            )

            cluster_height = (
                cluster_bottom - cluster_top
            )

            if (
                cluster_width
                < VectorGraphicClassifier
                .CHART_MIN_CLUSTER_WIDTH
                or cluster_height
                < VectorGraphicClassifier
                .CHART_MIN_CLUSTER_HEIGHT
            ):
                continue

            page_area = max(
                page.bbox.width
                * page.bbox.height,
                1.0,
            )

            cluster_area = max(
                cluster_width,
                0.0,
            ) * max(
                cluster_height,
                0.0,
            )

            page_coverage = (
                cluster_area / page_area
            )

            if (
                page_coverage
                > VectorGraphicClassifier
                .CHART_MAX_PAGE_COVERAGE
            ):
                continue

            long_line_count = sum(
                VectorGraphicClassifier
                ._is_chart_long_line(item)
                for item in cluster
            )

            marker_or_bar_count = sum(
                VectorGraphicClassifier
                ._is_chart_marker_or_bar(item)
                for item in cluster
            )

            colors = {
                item.stroke_color
                or item.fill_color
                for item in cluster
                if (
                    item.stroke_color
                    or item.fill_color
                )
            }

            has_multiple_colors = (
                len(colors) >= 2
            )

            has_grid_structure = (
                long_line_count
                >= VectorGraphicClassifier
                .CHART_MIN_LONG_LINES
            )

            has_data_graphics = (
                marker_or_bar_count
                >= VectorGraphicClassifier
                .CHART_MIN_MARKERS_OR_BARS
            )

            if (
                has_grid_structure
                and has_data_graphics
                and has_multiple_colors
            ):
                chart_graphics.extend(
                    cluster
                )

        return chart_graphics

    @staticmethod
    def _is_chart_long_line(
        graphic: VectorGraphic,
    ) -> bool:
        """
        Return True for likely chart axes, grid lines, or long
        series segments.
        """

        return (
            graphic.width
            >= VectorGraphicClassifier
            .LONG_LINE_MIN_LENGTH
            or graphic.height
            >= VectorGraphicClassifier
            .LONG_LINE_MIN_LENGTH
        )

    @staticmethod
    def _is_chart_marker_or_bar(
        graphic: VectorGraphic,
    ) -> bool:
        """
        Detect bars, legend markers, circular data points, and
        short line-series components.
        """
    
        if graphic.drawing_type in {
            "curve",
            "rectangle",
            "compound",
        }:
            return (
                graphic.width <= 110.0
                and graphic.height <= 230.0
            )
    
        if graphic.drawing_type == "line":
            has_visible_stroke = (
                graphic.stroke_color is not None
                and graphic.stroke_width >= 1.5
            )
    
            is_series_segment = (
                graphic.width <= 130.0
                and graphic.height <= 180.0
            )
    
            return (
                has_visible_stroke
                and is_series_segment
            )
    
        return False

    @staticmethod
    def _touches_page_edge(
        page,
        graphic: VectorGraphic,
    ) -> bool:
        """
        Return True when a graphic touches or extends beyond
        the page-edge region.

        Charts normally sit inside the content area, while cover
        and footer decorations often touch or extend beyond page
        boundaries.
        """

        margin = (
            VectorGraphicClassifier
            .CHART_PAGE_EDGE_MARGIN
        )

        return any(
            (
                graphic.left <= margin,
                graphic.top <= margin,
                graphic.right
                >= page.bbox.width - margin,
                graphic.bottom
                >= page.bbox.height - margin,
            )
        )

    @staticmethod
    def _graphic_near_cluster(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> bool:
        """
        Return True when a graphic is spatially close to
        any graphic already in a cluster.
        """

        distance = (
            VectorGraphicClassifier
            .CHART_CLUSTER_DISTANCE
        )

        for existing in cluster:

            horizontally_close = not (
                graphic.left
                > existing.right + distance
                or graphic.right
                < existing.left - distance
            )

            vertically_close = not (
                graphic.top
                > existing.bottom + distance
                or graphic.bottom
                < existing.top - distance
            )

            if (
                horizontally_close
                and vertically_close
            ):
                return True

        return False