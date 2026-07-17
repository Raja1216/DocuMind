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

    @staticmethod
    def analyze_page(page) -> None:
        """
        Classify all vector graphics on one page.
        """

        graphics = page.vector_graphics

        if not graphics:
            return

        chart_graphics = (
            VectorGraphicClassifier
            ._detect_chart_components(
                graphics
            )
        )

        chart_ids = {
            id(graphic)
            for graphic in chart_graphics
        }

        for graphic in graphics:

            if (
                id(graphic)
                in chart_ids
            ):
                graphic.category = (
                    VectorGraphicClassifier
                    .CATEGORY_CHART
                )

                # Chart rendering will be handled by the
                # dedicated Chart Engine later.
                graphic.should_render = False
                continue

            category = (
                VectorGraphicClassifier
                ._classify_individual_graphic(
                    page=page,
                    graphic=graphic,
                )
            )

            graphic.category = category

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

        if VectorGraphicClassifier._is_separator(
            graphic
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_SEPARATOR
            )

        if VectorGraphicClassifier._is_decorative(
            page=page,
            graphic=graphic,
        ):
            return (
                VectorGraphicClassifier
                .CATEGORY_DECORATIVE
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
        Detect large colored shapes near page boundaries.
        """

        if graphic.fill_color is None:
            return False

        near_page_edge = any(
            (
                graphic.left <= 20.0,
                graphic.top <= 20.0,
                graphic.right
                >= page.bbox.width - 20.0,
                graphic.bottom
                >= page.bbox.height - 20.0,
            )
        )

        is_large = (
            graphic.width >= 30.0
            or graphic.height >= 30.0
        )

        return (
            near_page_edge
            and is_large
        )

    @staticmethod
    def _detect_chart_components(
        graphics: list[VectorGraphic],
    ) -> list[VectorGraphic]:
        """
        Detect dense clusters of lines, bars, and point
        markers that likely form a chart.

        This is intentionally conservative.
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
                }
                and graphic.category
                != VectorGraphicClassifier
                .CATEGORY_BACKGROUND
            )
        ]

        if len(candidates) < (
            VectorGraphicClassifier
            .CHART_MIN_COMPONENTS
        ):
            return []

        clusters: list[list[VectorGraphic]] = []

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

        chart_graphics = []

        for cluster in clusters:

            if len(cluster) < (
                VectorGraphicClassifier
                .CHART_MIN_COMPONENTS
            ):
                continue

            has_long_lines = any(
                (
                    item.width
                    >= VectorGraphicClassifier
                    .LONG_LINE_MIN_LENGTH
                    or item.height
                    >= VectorGraphicClassifier
                    .LONG_LINE_MIN_LENGTH
                )
                for item in cluster
            )

            has_multiple_colors = (
                len(
                    {
                        item.stroke_color
                        or item.fill_color
                        for item in cluster
                        if (
                            item.stroke_color
                            or item.fill_color
                        )
                    }
                )
                >= 2
            )

            if (
                has_long_lines
                and has_multiple_colors
            ):
                chart_graphics.extend(
                    cluster
                )

        return chart_graphics

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