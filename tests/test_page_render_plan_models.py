from __future__ import annotations

import unittest

from types import SimpleNamespace

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


def make_item(
    item_id: str,
    kind: RenderItemKind,
    order: int,
    top: float,
    placement: RenderPlacement = (
        RenderPlacement.FLOW
    ),
    disposition: RenderDisposition = (
        RenderDisposition.EDITABLE
    ),
    page_number: int = 1,
) -> PageRenderItem:
    return PageRenderItem(
        order=order,

        page_number=page_number,

        item_id=item_id,

        kind=kind,

        placement=placement,

        disposition=disposition,

        role=RenderItemRole.BODY,

        bbox=Rectangle(
            left=50.0,
            top=top,
            right=300.0,
            bottom=top + 30.0,
        ),

        source=SimpleNamespace(
            name=item_id
        ),

        source_index=0,

        confidence=0.90,
    )


class PageRenderPlanModelTests(
    unittest.TestCase
):

    def test_page_initializes_empty_render_plan(
        self,
    ) -> None:
        page = Page(
            number=3,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),

            rotation=0,
        )

        self.assertEqual(
            page.render_plan.page_number,
            3,
        )

        self.assertEqual(
            page.render_plan.items,
            [],
        )

    def test_mixed_items_can_be_added(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        plan.add_item(
            make_item(
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=1,
                top=100.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="table:1",
                kind=(
                    RenderItemKind.TABLE
                ),
                order=2,
                top=150.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="image:1",
                kind=(
                    RenderItemKind.IMAGE
                ),
                order=3,
                top=250.0,
                disposition=(
                    RenderDisposition.VISUAL
                ),
            )
        )

        self.assertEqual(
            plan.item_count,
            3,
        )

        self.assertEqual(
            [
                item.kind
                for item
                in plan.items
            ],
            [
                RenderItemKind.PARAGRAPH,
                RenderItemKind.TABLE,
                RenderItemKind.IMAGE,
            ],
        )

    def test_duplicate_item_id_is_rejected(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        item = make_item(
            item_id="paragraph:1",
            kind=(
                RenderItemKind.PARAGRAPH
            ),
            order=1,
            top=100.0,
        )

        plan.add_item(
            item
        )

        with self.assertRaises(
            ValueError
        ):
            plan.add_item(
                make_item(
                    item_id="paragraph:1",
                    kind=(
                        RenderItemKind.PARAGRAPH
                    ),
                    order=2,
                    top=200.0,
                )
            )

    def test_item_from_different_page_is_rejected(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        with self.assertRaises(
            ValueError
        ):
            plan.add_item(
                make_item(
                    item_id="paragraph:1",
                    kind=(
                        RenderItemKind.PARAGRAPH
                    ),
                    order=1,
                    top=100.0,
                    page_number=2,
                )
            )

    def test_normalize_orders_is_deterministic(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        plan.add_item(
            make_item(
                item_id="paragraph:second",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=20,
                top=200.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="paragraph:first",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=10,
                top=100.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="table:middle",
                kind=(
                    RenderItemKind.TABLE
                ),
                order=15,
                top=150.0,
            )
        )

        plan.normalize_orders()

        self.assertEqual(
            [
                item.item_id
                for item
                in plan.items
            ],
            [
                "paragraph:first",
                "table:middle",
                "paragraph:second",
            ],
        )

        self.assertEqual(
            [
                item.order
                for item
                in plan.items
            ],
            [
                1,
                2,
                3,
            ],
        )

    def test_placement_and_disposition_filters(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        plan.add_item(
            make_item(
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=1,
                top=100.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="background:1",
                kind=(
                    RenderItemKind.VECTOR
                ),
                order=2,
                top=0.0,
                placement=(
                    RenderPlacement.BACKGROUND
                ),
                disposition=(
                    RenderDisposition.VISUAL
                ),
            )
        )

        plan.add_item(
            make_item(
                item_id="chart:1",
                kind=(
                    RenderItemKind.CHART
                ),
                order=3,
                top=300.0,
                disposition=(
                    RenderDisposition.VISUAL
                ),
            )
        )

        plan.add_item(
            make_item(
                item_id="noise:1",
                kind=(
                    RenderItemKind.VECTOR
                ),
                order=4,
                top=400.0,
                disposition=(
                    RenderDisposition.SKIP
                ),
            )
        )

        self.assertEqual(
            len(
                plan.flow_items
            ),
            2,
        )

        self.assertEqual(
            len(
                plan.background_items
            ),
            1,
        )

        self.assertEqual(
            len(
                plan.editable_items
            ),
            1,
        )

        self.assertEqual(
            len(
                plan.visual_items
            ),
            2,
        )

        self.assertEqual(
            len(
                plan.skipped_items
            ),
            1,
        )

    def test_count_by_kind(
        self,
    ) -> None:
        plan = PageRenderPlan(
            page_number=1
        )

        plan.add_item(
            make_item(
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=1,
                top=100.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="paragraph:2",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                order=2,
                top=130.0,
            )
        )

        plan.add_item(
            make_item(
                item_id="table:1",
                kind=(
                    RenderItemKind.TABLE
                ),
                order=3,
                top=200.0,
            )
        )

        counts = (
            plan.count_by_kind()
        )

        self.assertEqual(
            counts[
                RenderItemKind.PARAGRAPH
            ],
            2,
        )

        self.assertEqual(
            counts[
                RenderItemKind.TABLE
            ],
            1,
        )

        self.assertEqual(
            counts[
                RenderItemKind.IMAGE
            ],
            0,
        )

    def test_confidence_and_messages_are_normalized(
        self,
    ) -> None:
        item = make_item(
            item_id="paragraph:1",
            kind=(
                RenderItemKind.PARAGRAPH
            ),
            order=1,
            top=100.0,
        )

        item.set_confidence(
            4.5
        )

        item.add_reason(
            "Detected in page body."
        )

        item.add_reason(
            "Detected in page body."
        )

        item.add_warning(
            "Container is uncertain."
        )

        item.add_warning(
            "Container is uncertain."
        )

        self.assertEqual(
            item.confidence,
            1.0,
        )

        self.assertEqual(
            item.reasons,
            [
                "Detected in page body."
            ],
        )

        self.assertEqual(
            item.warnings,
            [
                "Container is uncertain."
            ],
        )


if __name__ == "__main__":
    unittest.main()