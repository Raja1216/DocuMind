from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page import (
    Page,
)
from src.models.page_render_plan import (
    PageRenderItem,
    PageRenderPlan,
    RenderDisposition,
    RenderItemKind,
    RenderItemRole,
    RenderPlacement,
)


@dataclass(slots=True)
class _RenderCandidate:
    """
    Internal render-plan candidate.

    explicit_order is populated for paragraphs that already
    have a reliable reading-order entry.
    """

    item: PageRenderItem

    explicit_order: float | None = None


class PageRenderPlanAnalyzer:
    """
    Combines all renderable page content into one stable,
    source-ordered PageRenderPlan.

    The analyzer is intentionally tolerant of slightly
    different source model names so that the render-plan layer
    remains independent from individual extraction engines.
    """

    TABLE_COLLECTION_NAMES = (
        "tables",
        "table_regions",
    )

    IMAGE_COLLECTION_NAMES = (
        "images",
        "image_regions",
    )

    CHART_COLLECTION_NAMES = (
        "charts",
        "chart_regions",
        "chart_groups",
    )

    VECTOR_COLLECTION_NAMES = (
        "vector_graphic_regions",
        "vector_regions",
        "vector_groups",
        "vectors",
    )

    READING_ORDER_COLLECTION_NAMES = (
        "reading_order_entries",
        "reading_order",
    )

    PARAGRAPH_COVERAGE_SKIP_THRESHOLD = 0.85

    TABLE_EDITABLE_CONFIDENCE_THRESHOLD = 0.55

    CONTAINER_TOLERANCE = 3.0

    DEFAULT_CONFIDENCE_BY_KIND = {
        RenderItemKind.PARAGRAPH: 0.90,
        RenderItemKind.TABLE: 0.70,
        RenderItemKind.IMAGE: 0.90,
        RenderItemKind.CHART: 0.75,
        RenderItemKind.VECTOR: 0.65,
        RenderItemKind.PAGE_FALLBACK: 1.00,
    }

    ROLE_ORDER = {
        RenderItemRole.HEADER: 0,

        RenderItemRole.BODY_SPANNING: 1,

        RenderItemRole.BODY: 2,

        RenderItemRole.COLUMN: 2,

        RenderItemRole.UNASSIGNED: 3,

        RenderItemRole.FOOTER: 4,

        RenderItemRole.DECORATION: 5,
    }

    PLACEMENT_ORDER = {
        RenderPlacement.BACKGROUND: 0,

        RenderPlacement.FLOATING: 1,

        RenderPlacement.FLOW: 2,

        RenderPlacement.OVERLAY: 3,
    }

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> PageRenderPlan:
        """
        Build and attach a fresh render plan for one page.

        Reanalysis clears all stale render-plan items.
        """

        plan = PageRenderPlan(
            page_number=int(
                page.number
            )
        )

        reading_order_by_region = (
            cls._build_reading_order_index(
                page
            )
        )

        candidates: list[
            _RenderCandidate
        ] = []

        used_source_ids: set[int] = set()

        cls._collect_paragraph_candidates(
            page=page,

            reading_order_by_region=(
                reading_order_by_region
            ),

            candidates=candidates,

            used_source_ids=(
                used_source_ids
            ),
        )

        cls._collect_collection_candidates(
            page=page,

            collection_names=(
                cls.TABLE_COLLECTION_NAMES
            ),

            default_kind=(
                RenderItemKind.TABLE
            ),

            candidates=candidates,

            used_source_ids=(
                used_source_ids
            ),
        )

        cls._collect_collection_candidates(
            page=page,

            collection_names=(
                cls.IMAGE_COLLECTION_NAMES
            ),

            default_kind=(
                RenderItemKind.IMAGE
            ),

            candidates=candidates,

            used_source_ids=(
                used_source_ids
            ),
        )

        cls._collect_collection_candidates(
            page=page,

            collection_names=(
                cls.CHART_COLLECTION_NAMES
            ),

            default_kind=(
                RenderItemKind.CHART
            ),

            candidates=candidates,

            used_source_ids=(
                used_source_ids
            ),
        )

        cls._collect_collection_candidates(
            page=page,

            collection_names=(
                cls.VECTOR_COLLECTION_NAMES
            ),

            default_kind=(
                RenderItemKind.VECTOR
            ),

            candidates=candidates,

            used_source_ids=(
                used_source_ids
            ),
        )

        fallback_candidate = (
            cls._build_page_fallback_candidate(
                page
            )
        )

        if fallback_candidate is not None:
            candidates.append(
                fallback_candidate
            )

        cls._suppress_covered_paragraphs(
            candidates
        )

        ordered_items = cls._order_candidates(
            page=page,
            candidates=candidates,
        )

        plan.replace_items(
            ordered_items
        )

        page.render_plan = plan

        return plan

    @classmethod
    def analyze_document(
        cls,
        document,
    ) -> None:
        """
        Rebuild render plans for every document page.
        """

        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.analyze_page(
                page
            )

    # ---------------------------------------------------------
    # Source collection
    # ---------------------------------------------------------

    @classmethod
    def _collect_paragraph_candidates(
        cls,
        page: Page,
        reading_order_by_region: dict[
            int,
            Any,
        ],
        candidates: list[_RenderCandidate],
        used_source_ids: set[int],
    ) -> None:
        paragraphs = getattr(
            page,
            "paragraph_regions",
            [],
        ) or []

        for source_index, paragraph in enumerate(
            paragraphs
        ):
            source_identity = id(
                paragraph
            )

            if source_identity in used_source_ids:
                continue

            used_source_ids.add(
                source_identity
            )

            bbox = cls._extract_bbox(
                paragraph
            )

            if bbox is None:
                continue

            region_number = (
                cls._safe_integer(
                    getattr(
                        paragraph,
                        "region_number",
                        None,
                    )
                )
            )

            reading_entry = (
                reading_order_by_region.get(
                    region_number
                )
                if region_number is not None
                else None
            )

            (
                role,
                layout_region_id,
                column_id,
            ) = cls._resolve_item_context(
                page=page,
                source=paragraph,
                bbox=bbox,
                reading_entry=(
                    reading_entry
                ),
            )

            marker_only = bool(
                getattr(
                    paragraph,
                    "is_list_marker_only",
                    False,
                )
            )

            disposition = (
                RenderDisposition.SKIP
                if marker_only
                else RenderDisposition.EDITABLE
            )

            placement = (
                RenderPlacement.FLOATING
                if role
                in {
                    RenderItemRole.HEADER,
                    RenderItemRole.FOOTER,
                }
                else RenderPlacement.FLOW
            )

            item = PageRenderItem(
                order=0,

                page_number=int(
                    page.number
                ),

                item_id=cls._build_item_id(
                    kind=(
                        RenderItemKind.PARAGRAPH
                    ),
                    source=paragraph,
                    source_index=source_index,
                    preferred_identifier=(
                        region_number
                    ),
                ),

                kind=(
                    RenderItemKind.PARAGRAPH
                ),

                placement=placement,

                disposition=disposition,

                role=role,

                bbox=bbox,

                source=paragraph,

                source_index=source_index,

                layout_region_id=(
                    layout_region_id
                ),

                column_id=column_id,

                confidence=(
                    cls._resolve_confidence(
                        source=paragraph,
                        kind=(
                            RenderItemKind
                            .PARAGRAPH
                        ),
                    )
                ),
            )

            if marker_only:
                item.add_reason(
                    (
                        "Detached marker-only paragraph is "
                        "represented by its associated list "
                        "content paragraph."
                    )
                )

            explicit_order = (
                cls._resolve_reading_order(
                    reading_entry
                )
            )

            candidates.append(
                _RenderCandidate(
                    item=item,
                    explicit_order=(
                        explicit_order
                    ),
                )
            )

    @classmethod
    def _collect_collection_candidates(
        cls,
        page: Page,
        collection_names: tuple[str, ...],
        default_kind: RenderItemKind,
        candidates: list[_RenderCandidate],
        used_source_ids: set[int],
    ) -> None:
        sources = cls._collect_unique_sources(
            page=page,
            collection_names=(
                collection_names
            ),
        )

        for source_index, source in enumerate(
            sources
        ):
            source_identity = id(
                source
            )

            if source_identity in used_source_ids:
                continue

            used_source_ids.add(
                source_identity
            )

            bbox = cls._extract_bbox(
                source
            )

            if bbox is None:
                continue

            kind = cls._resolve_item_kind(
                source=source,
                default_kind=(
                    default_kind
                ),
            )

            (
                role,
                layout_region_id,
                column_id,
            ) = cls._resolve_item_context(
                page=page,
                source=source,
                bbox=bbox,
                reading_entry=None,
            )

            confidence = (
                cls._resolve_confidence(
                    source=source,
                    kind=kind,
                )
            )

            (
                placement,
                disposition,
            ) = cls._resolve_render_strategy(
                source=source,
                kind=kind,
                role=role,
                confidence=confidence,
                page=page,
                bbox=bbox,
            )

            preferred_identifier = (
                cls._resolve_source_identifier(
                    source
                )
            )

            item = PageRenderItem(
                order=0,

                page_number=int(
                    page.number
                ),

                item_id=cls._build_item_id(
                    kind=kind,
                    source=source,
                    source_index=source_index,
                    preferred_identifier=(
                        preferred_identifier
                    ),
                ),

                kind=kind,

                placement=placement,

                disposition=disposition,

                role=role,

                bbox=bbox,

                source=source,

                source_index=source_index,

                layout_region_id=(
                    layout_region_id
                ),

                column_id=column_id,

                confidence=confidence,
            )

            cls._add_strategy_messages(
                item=item,
                source=source,
            )

            candidates.append(
                _RenderCandidate(
                    item=item
                )
            )

    @staticmethod
    def _collect_unique_sources(
        page: Page,
        collection_names: tuple[
            str,
            ...,
        ],
    ) -> list[Any]:
        sources: list[Any] = []

        used_ids: set[int] = set()

        for collection_name in collection_names:
            collection = getattr(
                page,
                collection_name,
                None,
            )

            if not collection:
                continue

            for source in collection:
                source_identity = id(
                    source
                )

                if source_identity in used_ids:
                    continue

                used_ids.add(
                    source_identity
                )

                sources.append(
                    source
                )

        return sources

    # ---------------------------------------------------------
    # Reading order
    # ---------------------------------------------------------

    @classmethod
    def _build_reading_order_index(
        cls,
        page: Page,
    ) -> dict[int, Any]:
        index: dict[int, Any] = {}

        entries: list[Any] = []

        for collection_name in (
            cls.READING_ORDER_COLLECTION_NAMES
        ):
            collection = getattr(
                page,
                collection_name,
                None,
            )

            if collection:
                entries.extend(
                    collection
                )

        for entry in entries:
            region_number = (
                cls._safe_integer(
                    getattr(
                        entry,
                        "paragraph_region_number",
                        getattr(
                            entry,
                            "region_number",
                            None,
                        ),
                    )
                )
            )

            if region_number is None:
                continue

            index[
                region_number
            ] = entry

        return index

    @classmethod
    def _order_candidates(
        cls,
        page: Page,
        candidates: list[_RenderCandidate],
    ) -> list[PageRenderItem]:
        paragraph_candidates = [
            candidate

            for candidate in candidates

            if (
                candidate.item.kind
                == RenderItemKind.PARAGRAPH

                and candidate.explicit_order
                is not None
            )
        ]

        sort_records: list[
            tuple[
                tuple[
                    float,
                    float,
                    float,
                    float,
                    float,
                    int,
                    str,
                ],
                PageRenderItem,
            ]
        ] = []

        for candidate in candidates:
            item = candidate.item

            anchor = (
                candidate.explicit_order
            )

            if anchor is None:
                anchor = cls._resolve_non_text_anchor(
                    item=item,

                    paragraph_candidates=(
                        paragraph_candidates
                    ),
                )

            placement_rank = float(
                cls.PLACEMENT_ORDER.get(
                    item.placement,
                    99,
                )
            )

            role_rank = float(
                cls.ROLE_ORDER.get(
                    item.role,
                    99,
                )
            )

            # Backgrounds are always ordered before semantic
            # page content, independent of their coordinates.
            if (
                item.placement
                == RenderPlacement.BACKGROUND
            ):
                anchor = -1_000_000.0

            sort_key = (
                placement_rank,
                role_rank,
                float(anchor),
                float(item.top),
                float(item.left),
                int(item.source_index),
                item.item_id,
            )

            sort_records.append(
                (
                    sort_key,
                    item,
                )
            )

        sort_records.sort(
            key=lambda record: record[0]
        )

        ordered_items = [
            item
            for _, item in sort_records
        ]

        for order, item in enumerate(
            ordered_items,
            start=1,
        ):
            item.order = order

        return ordered_items

    @classmethod
    def _resolve_non_text_anchor(
        cls,
        item: PageRenderItem,
        paragraph_candidates: list[
            _RenderCandidate
        ],
    ) -> float:
        compatible = [
            candidate

            for candidate in paragraph_candidates

            if cls._containers_are_compatible(
                item,
                candidate.item,
            )
        ]

        if not compatible:
            compatible = paragraph_candidates

        if not compatible:
            return (
                100_000.0
                + float(
                    item.top
                )
            )

        compatible.sort(
            key=lambda candidate: (
                float(
                    candidate.item.center_y
                ),
                float(
                    candidate.explicit_order
                    or 0.0
                ),
            )
        )

        preceding = [
            candidate

            for candidate in compatible

            if candidate.item.center_y
            <= item.center_y
        ]

        following = [
            candidate

            for candidate in compatible

            if candidate.item.center_y
            > item.center_y
        ]

        previous_candidate = (
            preceding[-1]
            if preceding
            else None
        )

        next_candidate = (
            following[0]
            if following
            else None
        )

        if (
            previous_candidate is not None
            and next_candidate is not None
        ):
            previous_order = float(
                previous_candidate
                .explicit_order
                or 0.0
            )

            next_order = float(
                next_candidate
                .explicit_order
                or previous_order + 1.0
            )

            return (
                previous_order
                + (
                    next_order
                    - previous_order
                )
                / 2.0
            )

        if previous_candidate is not None:
            return (
                float(
                    previous_candidate
                    .explicit_order
                    or 0.0
                )
                + 0.50
            )

        if next_candidate is not None:
            return (
                float(
                    next_candidate
                    .explicit_order
                    or 1.0
                )
                - 0.50
            )

        return (
            100_000.0
            + float(
                item.top
            )
        )

    @staticmethod
    def _containers_are_compatible(
        first: PageRenderItem,
        second: PageRenderItem,
    ) -> bool:
        if (
            first.role == RenderItemRole.HEADER
            or second.role
            == RenderItemRole.HEADER
        ):
            return (
                first.role
                == second.role
            )

        if (
            first.role == RenderItemRole.FOOTER
            or second.role
            == RenderItemRole.FOOTER
        ):
            return (
                first.role
                == second.role
            )

        if (
            first.column_id is not None
            and second.column_id is not None
        ):
            return (
                first.column_id
                == second.column_id
            )

        if (
            first.layout_region_id
            is not None

            and second.layout_region_id
            is not None
        ):
            return (
                first.layout_region_id
                == second.layout_region_id
            )

        body_roles = {
            RenderItemRole.BODY,
            RenderItemRole.BODY_SPANNING,
            RenderItemRole.COLUMN,
            RenderItemRole.UNASSIGNED,
        }

        return (
            first.role in body_roles
            and second.role in body_roles
        )

    # ---------------------------------------------------------
    # Duplicate text suppression
    # ---------------------------------------------------------

    @classmethod
    def _suppress_covered_paragraphs(
        cls,
        candidates: list[_RenderCandidate],
    ) -> None:
        covering_items = [
            candidate.item

            for candidate in candidates

            if (
                candidate.item.kind
                in {
                    RenderItemKind.TABLE,
                    RenderItemKind.IMAGE,
                    RenderItemKind.CHART,
                }

                and candidate.item.disposition
                != RenderDisposition.SKIP
            )
        ]

        paragraph_items = [
            candidate.item

            for candidate in candidates

            if (
                candidate.item.kind
                == RenderItemKind.PARAGRAPH

                and candidate.item.disposition
                != RenderDisposition.SKIP

                and candidate.item.role
                not in {
                    RenderItemRole.HEADER,
                    RenderItemRole.FOOTER,
                }
            )
        ]

        for paragraph in paragraph_items:
            if paragraph.area <= 0.0:
                continue

            for covering_item in covering_items:
                intersection_area = (
                    cls._intersection_area(
                        paragraph.bbox,
                        covering_item.bbox,
                    )
                )

                if intersection_area <= 0.0:
                    continue

                coverage_ratio = (
                    intersection_area
                    / paragraph.area
                )

                if (
                    coverage_ratio
                    < cls
                    .PARAGRAPH_COVERAGE_SKIP_THRESHOLD
                ):
                    continue

                paragraph.disposition = (
                    RenderDisposition.SKIP
                )

                paragraph.add_reason(
                    (
                        "Paragraph is substantially contained "
                        f"inside {covering_item.kind.value} "
                        f"{covering_item.item_id}; its text "
                        "will be represented by that object."
                    )
                )

                break

    # ---------------------------------------------------------
    # Context and strategy
    # ---------------------------------------------------------

    @classmethod
    def _resolve_item_context(
        cls,
        page: Page,
        source: Any,
        bbox: Rectangle,
        reading_entry: Any | None,
    ) -> tuple[
        RenderItemRole,
        int | None,
        int | None,
    ]:
        explicit_role = cls._normalize_role(
            cls._first_value(
                reading_entry,
                source,
                attribute_names=(
                    "role",
                    "reading_order_role",
                    "layout_role",
                ),
            )
        )

        explicit_layout_region_id = (
            cls._safe_integer(
                cls._first_value(
                    reading_entry,
                    source,
                    attribute_names=(
                        "layout_region_id",
                        "region_id",
                    ),
                )
            )
        )

        explicit_column_id = (
            cls._safe_integer(
                cls._first_value(
                    reading_entry,
                    source,
                    attribute_names=(
                        "column_id",
                        "column_region_id",
                    ),
                )
            )
        )

        layout_region = (
            cls._find_containing_region(
                getattr(
                    page,
                    "layout_regions",
                    [],
                )
                or [],

                bbox,
            )
        )

        column_region = (
            cls._find_containing_region(
                getattr(
                    page,
                    "column_regions",
                    [],
                )
                or [],

                bbox,
            )
        )

        layout_region_id = (
            explicit_layout_region_id
        )

        if (
            layout_region_id is None
            and layout_region is not None
        ):
            layout_region_id = (
                cls._resolve_source_identifier(
                    layout_region
                )
            )

        column_id = explicit_column_id

        if (
            column_id is None
            and column_region is not None
        ):
            column_id = (
                cls._resolve_source_identifier(
                    column_region
                )
            )

        if explicit_role is not None:
            return (
                explicit_role,
                layout_region_id,
                column_id,
            )

        layout_role = (
            cls._resolve_layout_region_role(
                layout_region
            )
        )

        if layout_role is not None:
            return (
                layout_role,
                layout_region_id,
                column_id,
            )

        if column_region is not None:
            return (
                RenderItemRole.COLUMN,
                layout_region_id,
                column_id,
            )

        columns = getattr(
            page,
            "column_regions",
            [],
        ) or []

        intersected_columns = [
            column

            for column in columns

            if cls._intersection_area(
                bbox,
                cls._extract_bbox(
                    column
                ),
            )
            > 0.0
        ]

        if len(
            intersected_columns
        ) >= 2:
            return (
                RenderItemRole.BODY_SPANNING,
                layout_region_id,
                None,
            )

        body_bbox = cls._resolve_page_body_bbox(
            page
        )

        if (
            body_bbox is not None
            and body_bbox.width > 0.0
            and (
                bbox.width
                / body_bbox.width
            )
            >= 0.72
        ):
            return (
                RenderItemRole.BODY_SPANNING,
                layout_region_id,
                None,
            )

        return (
            RenderItemRole.BODY,
            layout_region_id,
            column_id,
        )

    @classmethod
    def _resolve_render_strategy(
        cls,
        source: Any,
        kind: RenderItemKind,
        role: RenderItemRole,
        confidence: float,
        page: Page,
        bbox: Rectangle,
    ) -> tuple[
        RenderPlacement,
        RenderDisposition,
    ]:
        if kind == RenderItemKind.TABLE:
            placement = (
                RenderPlacement.FLOATING
                if role
                in {
                    RenderItemRole.HEADER,
                    RenderItemRole.FOOTER,
                }
                else RenderPlacement.FLOW
            )

            reliable = getattr(
                source,
                "is_reliable",
                None,
            )

            if reliable is False:
                return (
                    placement,
                    RenderDisposition.VISUAL,
                )

            if (
                confidence
                < cls
                .TABLE_EDITABLE_CONFIDENCE_THRESHOLD
            ):
                return (
                    placement,
                    RenderDisposition.VISUAL,
                )

            return (
                placement,
                RenderDisposition.EDITABLE,
            )

        if kind in {
            RenderItemKind.IMAGE,
            RenderItemKind.CHART,
        }:
            category = cls._resolve_category(
                source
            )

            if category in {
                "background",
                "watermark",
                "page_background",
            }:
                return (
                    RenderPlacement.BACKGROUND,
                    RenderDisposition.VISUAL,
                )

            if role in {
                RenderItemRole.HEADER,
                RenderItemRole.FOOTER,
            }:
                return (
                    RenderPlacement.FLOATING,
                    RenderDisposition.VISUAL,
                )

            return (
                RenderPlacement.FLOW,
                RenderDisposition.VISUAL,
            )

        if kind == RenderItemKind.VECTOR:
            category = cls._resolve_category(
                source
            )

            if category in {
                "background",
                "watermark",
                "page_background",
            }:
                return (
                    RenderPlacement.BACKGROUND,
                    RenderDisposition.VISUAL,
                )

            if category in {
                "bullet",
                "noise",
            }:
                return (
                    RenderPlacement.OVERLAY,
                    RenderDisposition.SKIP,
                )

            if category in {
                "decorative",
                "decoration",
            }:
                page_bbox = cls._extract_bbox(
                    page
                )

                page_area = (
                    page_bbox.width
                    * page_bbox.height
                    if page_bbox is not None
                    else 0.0
                )

                coverage = (
                    (
                        bbox.width
                        * bbox.height
                    )
                    / page_area

                    if page_area > 0.0
                    else 0.0
                )

                return (
                    (
                        RenderPlacement.BACKGROUND
                        if coverage >= 0.20
                        else RenderPlacement.OVERLAY
                    ),
                    RenderDisposition.VISUAL,
                )

            if category == "separator":
                return (
                    RenderPlacement.OVERLAY,
                    RenderDisposition.VISUAL,
                )

            return (
                RenderPlacement.OVERLAY,
                RenderDisposition.VISUAL,
            )

        if kind == RenderItemKind.PAGE_FALLBACK:
            return (
                RenderPlacement.BACKGROUND,
                RenderDisposition.FALLBACK,
            )

        return (
            RenderPlacement.FLOW,
            RenderDisposition.EDITABLE,
        )

    @classmethod
    def _resolve_item_kind(
        cls,
        source: Any,
        default_kind: RenderItemKind,
    ) -> RenderItemKind:
        if default_kind != RenderItemKind.VECTOR:
            return default_kind

        category = cls._resolve_category(
            source
        )

        if category == "chart":
            return RenderItemKind.CHART

        return RenderItemKind.VECTOR

    @classmethod
    def _add_strategy_messages(
        cls,
        item: PageRenderItem,
        source: Any,
    ) -> None:
        if (
            item.kind == RenderItemKind.TABLE
            and item.disposition
            == RenderDisposition.VISUAL
        ):
            item.add_warning(
                (
                    "Table confidence is insufficient for "
                    "native editable Word-table conversion."
                )
            )

        if (
            item.kind == RenderItemKind.VECTOR
            and item.disposition
            == RenderDisposition.SKIP
        ):
            item.add_reason(
                (
                    "Vector is already represented "
                    "semantically or classified as noise."
                )
            )

    # ---------------------------------------------------------
    # Page fallback
    # ---------------------------------------------------------

    @classmethod
    def _build_page_fallback_candidate(
        cls,
        page: Page,
    ) -> _RenderCandidate | None:
        policy = getattr(
            page,
            "conversion_policy",
            getattr(
                page,
                "policy",
                None,
            ),
        )

        use_page_fallback = bool(
            getattr(
                policy,
                "use_page_fallback",
                False,
            )
        )

        mode = getattr(
            policy,
            "mode",
            None,
        )

        mode_value = str(
            getattr(
                mode,
                "value",
                mode,
            )
            or ""
        ).casefold()

        if mode_value in {
            "image_fallback",
            "page_fallback",
        }:
            use_page_fallback = True

        if not use_page_fallback:
            return None

        page_bbox = cls._extract_bbox(
            page
        )

        if page_bbox is None:
            return None

        item = PageRenderItem(
            order=0,

            page_number=int(
                page.number
            ),

            item_id=(
                f"page_fallback:{page.number}"
            ),

            kind=(
                RenderItemKind.PAGE_FALLBACK
            ),

            placement=(
                RenderPlacement.BACKGROUND
            ),

            disposition=(
                RenderDisposition.FALLBACK
            ),

            role=(
                RenderItemRole.BODY
            ),

            bbox=page_bbox,

            source=page,

            source_index=0,

            confidence=1.0,
        )

        item.add_reason(
            (
                "Page conversion policy explicitly requests "
                "a visual fallback."
            )
        )

        return _RenderCandidate(
            item=item
        )

    # ---------------------------------------------------------
    # Geometry
    # ---------------------------------------------------------

    @classmethod
    def _extract_bbox(
        cls,
        source: Any,
    ) -> Rectangle | None:
        if source is None:
            return None

        bbox = getattr(
            source,
            "bbox",
            None,
        )

        if bbox is not None:
            left = getattr(
                bbox,
                "left",
                None,
            )

            top = getattr(
                bbox,
                "top",
                None,
            )

            right = getattr(
                bbox,
                "right",
                None,
            )

            bottom = getattr(
                bbox,
                "bottom",
                None,
            )

        else:
            left = getattr(
                source,
                "left",
                None,
            )

            top = getattr(
                source,
                "top",
                None,
            )

            right = getattr(
                source,
                "right",
                None,
            )

            bottom = getattr(
                source,
                "bottom",
                None,
            )

        values = (
            left,
            top,
            right,
            bottom,
        )

        if any(
            value is None
            for value in values
        ):
            return None

        try:
            left_value = float(
                left
            )

            top_value = float(
                top
            )

            right_value = float(
                right
            )

            bottom_value = float(
                bottom
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if right_value < left_value:
            (
                left_value,
                right_value,
            ) = (
                right_value,
                left_value,
            )

        if bottom_value < top_value:
            (
                top_value,
                bottom_value,
            ) = (
                bottom_value,
                top_value,
            )

        return Rectangle(
            left=left_value,
            top=top_value,
            right=right_value,
            bottom=bottom_value,
        )

    @classmethod
    def _find_containing_region(
        cls,
        regions: Iterable[Any],
        bbox: Rectangle,
    ) -> Any | None:
        matches: list[
            tuple[
                float,
                Any,
            ]
        ] = []

        for region in regions:
            region_bbox = cls._extract_bbox(
                region
            )

            if region_bbox is None:
                continue

            intersection = (
                cls._intersection_area(
                    bbox,
                    region_bbox,
                )
            )

            item_area = max(
                bbox.width
                * bbox.height,
                1.0,
            )

            coverage = (
                intersection
                / item_area
            )

            if coverage < 0.75:
                continue

            region_area = max(
                region_bbox.width
                * region_bbox.height,
                1.0,
            )

            matches.append(
                (
                    region_area,
                    region,
                )
            )

        if not matches:
            return None

        matches.sort(
            key=lambda value: value[0]
        )

        return matches[0][1]

    @staticmethod
    def _intersection_area(
        first: Rectangle | None,
        second: Rectangle | None,
    ) -> float:
        if (
            first is None
            or second is None
        ):
            return 0.0

        intersection_width = max(
            min(
                float(
                    first.right
                ),
                float(
                    second.right
                ),
            )
            - max(
                float(
                    first.left
                ),
                float(
                    second.left
                ),
            ),
            0.0,
        )

        intersection_height = max(
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

        return (
            intersection_width
            * intersection_height
        )

    @classmethod
    def _resolve_page_body_bbox(
        cls,
        page: Page,
    ) -> Rectangle | None:
        profile = getattr(
            page,
            "profile",
            None,
        )

        for attribute_name in (
            "body_bbox",
            "page_body_bbox",
        ):
            body_bbox = getattr(
                profile,
                attribute_name,
                None,
            )

            if body_bbox is not None:
                normalized = cls._extract_bbox(
                    body_bbox
                )

                if normalized is not None:
                    return normalized

        for region in getattr(
            page,
            "layout_regions",
            [],
        ) or []:
            role = cls._resolve_layout_region_role(
                region
            )

            if role in {
                RenderItemRole.BODY,
                RenderItemRole.BODY_SPANNING,
            }:
                return cls._extract_bbox(
                    region
                )

        return cls._extract_bbox(
            page
        )

    # ---------------------------------------------------------
    # Value normalization
    # ---------------------------------------------------------

    @classmethod
    def _resolve_confidence(
        cls,
        source: Any,
        kind: RenderItemKind,
    ) -> float:
        for attribute_name in (
            "confidence",
            "detection_confidence",
            "classification_confidence",
            "score",
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            if value is None:
                continue

            try:
                return max(
                    0.0,
                    min(
                        float(
                            value
                        ),
                        1.0,
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return cls.DEFAULT_CONFIDENCE_BY_KIND[
            kind
        ]

    @staticmethod
    def _resolve_reading_order(
        reading_entry: Any | None,
    ) -> float | None:
        if reading_entry is None:
            return None

        for attribute_name in (
            "order",
            "reading_order",
        ):
            value = getattr(
                reading_entry,
                attribute_name,
                None,
            )

            if value is None:
                continue

            try:
                return float(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    @classmethod
    def _normalize_role(
        cls,
        value: Any,
    ) -> RenderItemRole | None:
        if value is None:
            return None

        if isinstance(
            value,
            RenderItemRole,
        ):
            return value

        normalized = str(
            getattr(
                value,
                "value",
                value,
            )
        ).strip().casefold()

        mapping = {
            "header": RenderItemRole.HEADER,

            "body": RenderItemRole.BODY,

            "body_spanning": (
                RenderItemRole.BODY_SPANNING
            ),

            "spanning": (
                RenderItemRole.BODY_SPANNING
            ),

            "column": RenderItemRole.COLUMN,

            "footer": RenderItemRole.FOOTER,

            "decoration": (
                RenderItemRole.DECORATION
            ),

            "decorative": (
                RenderItemRole.DECORATION
            ),

            "unassigned": (
                RenderItemRole.UNASSIGNED
            ),
        }

        return mapping.get(
            normalized
        )

    @classmethod
    def _resolve_layout_region_role(
        cls,
        region: Any | None,
    ) -> RenderItemRole | None:
        if region is None:
            return None

        for attribute_name in (
            "role",
            "region_type",
            "kind",
            "type",
        ):
            value = getattr(
                region,
                attribute_name,
                None,
            )

            role = cls._normalize_role(
                value
            )

            if role is not None:
                return role

        return None

    @staticmethod
    def _resolve_category(
        source: Any,
    ) -> str:
        for attribute_name in (
            "category",
            "classification",
            "vector_type",
            "kind",
            "type",
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            if value is None:
                continue

            return str(
                getattr(
                    value,
                    "value",
                    value,
                )
            ).strip().casefold()

        return ""

    @classmethod
    def _resolve_source_identifier(
        cls,
        source: Any,
    ) -> int | None:
        for attribute_name in (
            "region_number",
            "table_number",
            "image_number",
            "chart_number",
            "group_number",
            "column_number",
            "column_id",
            "id",
        ):
            value = cls._safe_integer(
                getattr(
                    source,
                    attribute_name,
                    None,
                )
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _build_item_id(
        kind: RenderItemKind,
        source: Any,
        source_index: int,
        preferred_identifier: int | None,
    ) -> str:
        identifier = (
            preferred_identifier
            if preferred_identifier is not None
            else source_index + 1
        )

        return (
            f"{kind.value}:{identifier}"
        )

    @staticmethod
    def _safe_integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _first_value(
        *sources: Any,
        attribute_names: tuple[
            str,
            ...,
        ],
    ) -> Any:
        for source in sources:
            if source is None:
                continue

            for attribute_name in (
                attribute_names
            ):
                value = getattr(
                    source,
                    attribute_name,
                    None,
                )

                if value is not None:
                    return value

        return None