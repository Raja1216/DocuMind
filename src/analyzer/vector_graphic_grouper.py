from __future__ import annotations

from src.models.vector_graphic import VectorGraphic
from src.models.vector_graphic_region import (
    VectorGraphicRegion,
)


class VectorGraphicGrouper:
    """
    Groups nearby renderable vector graphics into logical
    visual regions.

    The grouping rules intentionally avoid transitive merging
    of unrelated artwork across the entire page.
    """

    GROUP_DISTANCE = 12.0

    MAX_REGION_WIDTH_RATIO = 0.90
    MAX_REGION_HEIGHT_RATIO = 0.55
    MAX_REGION_AREA_RATIO = 0.45

    @staticmethod
    def group(page) -> None:
        """
        Build vector regions for one page.
        """

        page.vector_regions.clear()

        graphics = [
            graphic
            for graphic in page.vector_graphics
            if graphic.should_render
        ]

        if not graphics:
            return

        # Process graphics from top to bottom and left to right.
        graphics.sort(
            key=lambda graphic: (
                graphic.top,
                graphic.left,
            )
        )

        clusters: list[list[VectorGraphic]] = []

        for graphic in graphics:
            best_cluster_index = None
            best_distance = None

            for index, cluster in enumerate(clusters):

                if not VectorGraphicGrouper._same_category_group(
                    graphic=graphic,
                    cluster=cluster,
                ):
                    continue
                
                is_strongly_overlapping = (
                    VectorGraphicGrouper
                    ._strongly_overlaps_cluster(
                        graphic=graphic,
                        cluster=cluster,
                    )
                )

                is_nearby = (
                    VectorGraphicGrouper
                    ._near_cluster(
                        graphic=graphic,
                        cluster=cluster,
                    )
                )

                if not is_nearby:
                    continue
                
                if (
                    not is_strongly_overlapping
                    and not (
                        VectorGraphicGrouper
                        ._region_size_allowed(
                            page=page,
                            cluster=cluster,
                            new_graphic=graphic,
                        )
                    )
                ):
                    continue
                
                distance = (
                    VectorGraphicGrouper
                    ._distance_to_cluster(
                        graphic=graphic,
                        cluster=cluster,
                    )
                )

                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_distance = distance
                    best_cluster_index = index

            if best_cluster_index is None:
                clusters.append(
                    [graphic]
                )
            else:
                clusters[
                    best_cluster_index
                ].append(
                    graphic
                )

        for region_number, cluster in enumerate(
            clusters,
            start=1,
        ):
            page.vector_regions.append(
                VectorGraphicGrouper._build_region(
                    graphics=cluster,
                    region_number=region_number,
                )
            )

    @staticmethod
    def _same_category_group(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> bool:
        """
        Prevent unrelated vector categories from being merged.

        Unknown graphics may still group with other unknown
        graphics, while decorative graphics group only with
        decorative graphics.
        """

        cluster_categories = {
            item.category
            for item in cluster
        }

        return graphic.category in cluster_categories

    @staticmethod
    def _strongly_overlaps_cluster(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> bool:
        """
        Return True only when the graphic strongly overlaps at
        least one existing graphic.
    
        This avoids merging large artworks whose bounding boxes
        intersect by only a small amount.
        """
    
        return any(
            VectorGraphicGrouper._strongly_overlaps(
                graphic,
                item,
            )
            for item in cluster
        )
    
    
    @staticmethod
    def _strongly_overlaps(
        first: VectorGraphic,
        second: VectorGraphic,
    ) -> bool:
        """
        Determine whether two bounding boxes have a meaningful
        overlap rather than a small accidental intersection.
        """
    
        intersection_left = max(
            first.left,
            second.left,
        )
    
        intersection_top = max(
            first.top,
            second.top,
        )
    
        intersection_right = min(
            first.right,
            second.right,
        )
    
        intersection_bottom = min(
            first.bottom,
            second.bottom,
        )
    
        intersection_width = max(
            intersection_right - intersection_left,
            0.0,
        )
    
        intersection_height = max(
            intersection_bottom - intersection_top,
            0.0,
        )
    
        if (
            intersection_width <= 0.0
            or intersection_height <= 0.0
        ):
            return False
    
        first_width = max(
            first.right - first.left,
            0.01,
        )
    
        first_height = max(
            first.bottom - first.top,
            0.01,
        )
    
        second_width = max(
            second.right - second.left,
            0.01,
        )
    
        second_height = max(
            second.bottom - second.top,
            0.01,
        )
    
        width_overlap_ratio = (
            intersection_width
            / min(
                first_width,
                second_width,
            )
        )
    
        height_overlap_ratio = (
            intersection_height
            / min(
                first_height,
                second_height,
            )
        )
    
        intersection_area = (
            intersection_width
            * intersection_height
        )
    
        smaller_area = min(
            first_width * first_height,
            second_width * second_height,
        )
    
        area_overlap_ratio = (
            intersection_area
            / max(
                smaller_area,
                0.01,
            )
        )
    
        # Strong in both dimensions.
        if (
            width_overlap_ratio >= 0.20
            and height_overlap_ratio >= 0.20
        ):
            return True
    
        # Or a substantial percentage of the smaller graphic is
        # covered by the other graphic.
        return area_overlap_ratio >= 0.15

    @staticmethod
    def _overlaps_cluster(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> bool:
        """
        Return True when the graphic's bounding box directly
        overlaps at least one graphic in the cluster.

        Overlapping paths generally form one visual object, such
        as layered waves, logos, or multi-colour decorations.
        """

        return any(
            VectorGraphicGrouper._overlaps(
                graphic,
                item,
            )
            for item in cluster
        )

    @staticmethod
    def _overlaps(
        first: VectorGraphic,
        second: VectorGraphic,
    ) -> bool:
        """
        Check whether two bounding rectangles overlap or touch.
        """

        return not (
            first.right < second.left
            or first.left > second.right
            or first.bottom < second.top
            or first.top > second.bottom
        )

    @staticmethod
    def _near_cluster(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> bool:
        """
        Return True when the graphic overlaps or is close to at
        least one graphic in the cluster.
        """

        return any(
            VectorGraphicGrouper._near(
                graphic,
                item,
            )
            for item in cluster
        )

    @staticmethod
    def _near(
        first: VectorGraphic,
        second: VectorGraphic,
    ) -> bool:
        """
        Return True when two graphics overlap or are separated by
        only a small horizontal, vertical, or diagonal gap.
        """

        if VectorGraphicGrouper._overlaps(
            first,
            second,
        ):
            return True

        margin = (
            VectorGraphicGrouper
            .GROUP_DISTANCE
        )

        horizontal_gap = max(
            second.left - first.right,
            first.left - second.right,
            0.0,
        )

        vertical_gap = max(
            second.top - first.bottom,
            first.top - second.bottom,
            0.0,
        )

        return (
            horizontal_gap <= margin
            and vertical_gap <= margin
        )

    @staticmethod
    def _distance_to_cluster(
        graphic: VectorGraphic,
        cluster: list[VectorGraphic],
    ) -> float:
        """
        Return the shortest bounding-box distance between a
        graphic and the cluster.
        """

        return min(
            VectorGraphicGrouper
            ._bounding_box_distance(
                graphic,
                item,
            )
            for item in cluster
        )

    @staticmethod
    def _bounding_box_distance(
        first: VectorGraphic,
        second: VectorGraphic,
    ) -> float:
        horizontal_gap = max(
            second.left - first.right,
            first.left - second.right,
            0.0,
        )

        vertical_gap = max(
            second.top - first.bottom,
            first.top - second.bottom,
            0.0,
        )

        return (
            horizontal_gap ** 2
            + vertical_gap ** 2
        ) ** 0.5

    @staticmethod
    def _region_size_allowed(
        page,
        cluster: list[VectorGraphic],
        new_graphic: VectorGraphic,
    ) -> bool:
        """
        Reject additions that would cause an unrelated
        near-page-sized region.

        Large individual cover waves are still allowed because
        the check applies only when adding another graphic.
        """

        combined = [
            *cluster,
            new_graphic,
        ]

        left = min(
            item.left
            for item in combined
        )

        top = min(
            item.top
            for item in combined
        )

        right = max(
            item.right
            for item in combined
        )

        bottom = max(
            item.bottom
            for item in combined
        )

        width = max(
            right - left,
            0.0,
        )

        height = max(
            bottom - top,
            0.0,
        )

        page_width = max(
            page.bbox.width,
            1.0,
        )

        page_height = max(
            page.bbox.height,
            1.0,
        )

        width_ratio = (
            width / page_width
        )

        height_ratio = (
            height / page_height
        )

        area_ratio = (
            width * height
        ) / (
            page_width * page_height
        )

        # Allow a group that is wide but not tall, such as the
        # central cover-page wave.
        if (
            width_ratio
            > VectorGraphicGrouper
            .MAX_REGION_WIDTH_RATIO
            and height_ratio
            > VectorGraphicGrouper
            .MAX_REGION_HEIGHT_RATIO
        ):
            return False

        if (
            area_ratio
            > VectorGraphicGrouper
            .MAX_REGION_AREA_RATIO
            and len(cluster) >= 2
        ):
            return False

        return True

    @staticmethod
    def _build_region(
        graphics: list[VectorGraphic],
        region_number: int,
    ) -> VectorGraphicRegion:
        if not graphics:
            raise ValueError(
                "Cannot build a vector region from an empty graphics list."
            )

        left = min(
            graphic.left
            for graphic in graphics
        )

        top = min(
            graphic.top
            for graphic in graphics
        )

        right = max(
            graphic.right
            for graphic in graphics
        )

        bottom = max(
            graphic.bottom
            for graphic in graphics
        )

        return VectorGraphicRegion(
            page_number=graphics[0].page_number,
            region_number=region_number,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            graphics=graphics,
        )