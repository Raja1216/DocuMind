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
    CHART_CLUSTER_DISTANCE = 25.0
    
    CHART_PAGE_EDGE_MARGIN = 40.0
    CHART_MIN_CLUSTER_WIDTH = 120.0
    CHART_MIN_CLUSTER_HEIGHT = 80.0

    CHART_MAX_PAGE_COVERAGE = 0.65
    CHART_MIN_LONG_LINES = 2
    CHART_MIN_MARKERS_OR_BARS = 3

    @staticmethod
    def analyze_page(page) -> None:
        """
        Classify page vector graphics in two passes.

        Pass 1:
        Detect obvious backgrounds, bullets, noise,
        separators, and decorative edge graphics.

        Pass 2:
        Run chart detection only on the remaining unknown
        graphics. This prevents full-page backgrounds and
        decorative artwork from joining chart clusters.
        """

        graphics = page.vector_graphics

        if not graphics:
            return

        # First classify obvious, non-chart graphics.
        chart_candidates: list[VectorGraphic] = []

        for graphic in graphics:

            category = (
                VectorGraphicClassifier
                ._classify_individual_graphic(
                    page=page,
                    graphic=graphic,
                )
            )

            graphic.category = category

            if category == (
                VectorGraphicClassifier
                .CATEGORY_UNKNOWN
            ):
                chart_candidates.append(
                    graphic
                )
                continue

            graphic.should_render = (
                category
                not in {
                    VectorGraphicClassifier
                    .CATEGORY_BACKGROUND,
                    VectorGraphicClassifier
                    .CATEGORY_BULLET,
                    VectorGraphicClassifier
                    .CATEGORY_NOISE,
                }
            )

        # Detect charts only among graphics not already identified
        # as backgrounds, decorations, bullets, or separators.
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

        for graphic in chart_candidates:

            if id(graphic) in chart_ids:
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_CHART
                )

                # The dedicated Chart Engine will process these.
                graphic.should_render = False
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
        Detect dense drawing clusters that resemble charts.

        Only previously unclassified graphics are provided to
        this method. Decorative edge graphics and full-page
        backgrounds must never be considered chart candidates.
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

            matching_cluster = None

            for cluster in clusters:
                if (
                    VectorGraphicClassifier
                    ._graphic_near_cluster(
                        graphic=graphic,
                        cluster=cluster,
                    )
                ):
                    matching_cluster = cluster
                    break

            if matching_cluster is None:
                clusters.append(
                    [graphic]
                )
            else:
                matching_cluster.append(
                    graphic
                )

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
                graphic.left
                for graphic in cluster
            )

            cluster_top = min(
                graphic.top
                for graphic in cluster
            )

            cluster_right = max(
                graphic.right
                for graphic in cluster
            )

            cluster_bottom = max(
                graphic.bottom
                for graphic in cluster
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
                (
                    graphic.width
                    >= VectorGraphicClassifier
                    .LONG_LINE_MIN_LENGTH
                    or graphic.height
                    >= VectorGraphicClassifier
                    .LONG_LINE_MIN_LENGTH
                )
                for graphic in cluster
            )

            marker_or_bar_count = sum(
                (
                    graphic.drawing_type
                    in {
                        "curve",
                        "rectangle",
                        "compound",
                    }
                    and graphic.width <= 100.0
                    and graphic.height <= 220.0
                )
                for graphic in cluster
            )

            colors = {
                graphic.stroke_color
                or graphic.fill_color
                for graphic in cluster
                if (
                    graphic.stroke_color
                    or graphic.fill_color
                )
            }

            has_multiple_colors = (
                len(colors) >= 2
            )

            if (
                long_line_count
                >= VectorGraphicClassifier
                .CHART_MIN_LONG_LINES
                and marker_or_bar_count
                >= VectorGraphicClassifier
                .CHART_MIN_MARKERS_OR_BARS
                and has_multiple_colors
            ):
                chart_graphics.extend(
                    cluster
                )

        return chart_graphics

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