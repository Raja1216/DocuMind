from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.models.geometry.rectangle import (
    Rectangle,
)


class RenderItemKind(str, Enum):
    """
    Type of source content represented by one render-plan item.
    """

    PARAGRAPH = "paragraph"

    TABLE = "table"

    IMAGE = "image"

    CHART = "chart"

    VECTOR = "vector"

    PAGE_FALLBACK = "page_fallback"


class RenderPlacement(str, Enum):
    """
    How an item participates in editable Word layout.
    """

    # Participates in normal Word document flow.
    FLOW = "flow"

    # Positioned relative to text but does not consume normal
    # paragraph flow.
    FLOATING = "floating"

    # Rendered behind the editable page content.
    BACKGROUND = "background"

    # Rendered above existing content.
    OVERLAY = "overlay"


class RenderDisposition(str, Enum):
    """
    Conversion strategy for one render-plan item.
    """

    # Convert into a native editable Word object.
    EDITABLE = "editable"

    # Render as a visual object, normally an image.
    VISUAL = "visual"

    # Use a region or page-level fallback image.
    FALLBACK = "fallback"

    # Keep the item in the diagnostic plan but do not export it.
    SKIP = "skip"


class RenderItemRole(str, Enum):
    """
    Semantic position of an item on the source page.
    """

    HEADER = "header"

    BODY = "body"

    BODY_SPANNING = "body_spanning"

    COLUMN = "column"

    FOOTER = "footer"

    DECORATION = "decoration"

    UNASSIGNED = "unassigned"


@dataclass(slots=True)
class PageRenderItem:
    """
    One normalized item in a PDF page's render plan.

    The `source` field points to the existing ParagraphRegion,
    Table, Image, VectorGraphicRegion, chart group, or fallback
    object. The render-plan model does not duplicate source
    content.
    """

    order: int

    page_number: int

    item_id: str

    kind: RenderItemKind

    placement: RenderPlacement

    disposition: RenderDisposition

    role: RenderItemRole

    bbox: Rectangle

    source: Any = field(
        repr=False
    )

    source_index: int = 0

    layout_region_id: int | None = None

    column_id: int | None = None

    confidence: float = 0.0

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def left(self) -> float:
        return float(
            self.bbox.left
        )

    @property
    def top(self) -> float:
        return float(
            self.bbox.top
        )

    @property
    def right(self) -> float:
        return float(
            self.bbox.right
        )

    @property
    def bottom(self) -> float:
        return float(
            self.bbox.bottom
        )

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

    @property
    def area(self) -> float:
        return (
            self.width
            * self.height
        )

    @property
    def is_flow_item(self) -> bool:
        return (
            self.placement
            == RenderPlacement.FLOW
        )

    @property
    def is_editable(self) -> bool:
        return (
            self.disposition
            == RenderDisposition.EDITABLE
        )

    @property
    def is_visual(self) -> bool:
        return (
            self.disposition
            in {
                RenderDisposition.VISUAL,
                RenderDisposition.FALLBACK,
            }
        )

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Store confidence within the supported range.
        """

        self.confidence = max(
            0.0,
            min(
                float(
                    confidence
                ),
                1.0,
            ),
        )

    def add_reason(
        self,
        reason: str,
    ) -> None:
        normalized = str(
            reason
        ).strip()

        if (
            normalized
            and normalized
            not in self.reasons
        ):
            self.reasons.append(
                normalized
            )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )


@dataclass(slots=True)
class PageRenderPlan:
    """
    Ordered rendering instructions for one PDF page.

    Future exporters will consume this plan instead of reading
    page.paragraph_regions, page.tables and page.images
    independently.
    """

    page_number: int

    items: list[PageRenderItem] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def flow_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.placement
            == RenderPlacement.FLOW
            and item.disposition
            != RenderDisposition.SKIP
        ]

    @property
    def background_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.placement
            == RenderPlacement.BACKGROUND
            and item.disposition
            != RenderDisposition.SKIP
        ]

    @property
    def floating_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.placement
            in {
                RenderPlacement.FLOATING,
                RenderPlacement.OVERLAY,
            }
            and item.disposition
            != RenderDisposition.SKIP
        ]

    @property
    def editable_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.disposition
            == RenderDisposition.EDITABLE
        ]

    @property
    def visual_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.disposition
            in {
                RenderDisposition.VISUAL,
                RenderDisposition.FALLBACK,
            }
        ]

    @property
    def skipped_items(
        self,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.disposition
            == RenderDisposition.SKIP
        ]

    @property
    def item_count(
        self,
    ) -> int:
        return len(
            self.items
        )

    def add_item(
        self,
        item: PageRenderItem,
    ) -> None:
        """
        Add one item while enforcing page and ID consistency.
        """

        if (
            item.page_number
            != self.page_number
        ):
            raise ValueError(
                (
                    "Render item page number does not match "
                    "the containing page render plan: "
                    f"{item.page_number} != "
                    f"{self.page_number}"
                )
            )

        if any(
            existing.item_id
            == item.item_id
            for existing in self.items
        ):
            raise ValueError(
                (
                    "Duplicate page render item ID: "
                    f"{item.item_id}"
                )
            )

        self.items.append(
            item
        )

    def replace_items(
        self,
        items: list[PageRenderItem],
    ) -> None:
        """
        Replace stale plan items during reanalysis.
        """

        self.items.clear()

        for item in items:
            self.add_item(
                item
            )

    def normalize_orders(
        self,
    ) -> None:
        """
        Sort items deterministically and assign consecutive
        one-based order values.

        The future render-plan analyzer will calculate initial
        order anchors. This method makes final ordering stable.
        """

        self.items.sort(
            key=lambda item: (
                int(
                    item.order
                ),
                float(
                    item.top
                ),
                float(
                    item.left
                ),
                int(
                    item.source_index
                ),
                item.item_id,
            )
        )

        for order, item in enumerate(
            self.items,
            start=1,
        ):
            item.order = order

    def items_of_kind(
        self,
        kind: RenderItemKind,
    ) -> list[PageRenderItem]:
        return [
            item
            for item in self.items
            if item.kind == kind
        ]

    def count_by_kind(
        self,
    ) -> dict[RenderItemKind, int]:
        counts = {
            kind: 0
            for kind in RenderItemKind
        }

        for item in self.items:
            counts[
                item.kind
            ] += 1

        return counts

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )