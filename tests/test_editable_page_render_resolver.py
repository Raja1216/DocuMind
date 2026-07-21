from __future__ import annotations

import unittest

from types import SimpleNamespace
from unittest.mock import patch

from src.exporter.editable_page_render_resolver import (
    EditablePageRenderResolver,
    EditableRenderAction,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page_render_plan import (
    PageRenderItem,
    PageRenderPlan,
    RenderDisposition,
    RenderItemKind,
    RenderItemRole,
    RenderPlacement,
)


def make_paragraph(
    region_number: int,
    text: str,
):
    return SimpleNamespace(
        region_number=region_number,
        text=text,
        is_list_marker_only=False,
    )


def make_layout_item(
    paragraph,
):
    return SimpleNamespace(
        paragraph=paragraph,
        content_left=50.0,
    )


def make_render_item(
    order: int,
    item_id: str,
    kind: RenderItemKind,
    source,
    disposition: RenderDisposition = (
        RenderDisposition.EDITABLE
    ),
    placement: RenderPlacement = (
        RenderPlacement.FLOW
    ),
    role: RenderItemRole = (
        RenderItemRole.BODY
    ),
):
    return PageRenderItem(
        order=order,

        page_number=1,

        item_id=item_id,

        kind=kind,

        placement=placement,

        disposition=disposition,

        role=role,

        bbox=Rectangle(
            left=50.0,
            top=float(
                order * 50
            ),
            right=400.0,
            bottom=float(
                order * 50 + 20
            ),
        ),

        source=source,

        source_index=order - 1,

        confidence=0.90,
    )


def make_page():
    return SimpleNamespace(
        number=1,
        render_plan=PageRenderPlan(
            page_number=1
        ),
    )


class EditablePageRenderResolverTests(
    unittest.TestCase
):

    def test_render_plan_order_controls_paragraph_order(
        self,
    ) -> None:
        page = make_page()

        first = make_paragraph(
            1,
            "First",
        )

        second = make_paragraph(
            2,
            "Second",
        )

        # Legacy layout order is intentionally reversed.
        legacy_layout_items = [
            make_layout_item(
                second
            ),
            make_layout_item(
                first
            ),
        ]

        page.render_plan.add_item(
            make_render_item(
                order=1,
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=first,
            )
        )

        page.render_plan.add_item(
            make_render_item(
                order=2,
                item_id="paragraph:2",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=second,
            )
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=(
                legacy_layout_items
            ),
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            [
                instruction.source.text
                for instruction
                in result.paragraph_instructions
            ],
            [
                "First",
                "Second",
            ],
        )

    def test_skipped_paragraph_is_not_rendered(
        self,
    ) -> None:
        page = make_page()

        paragraph = make_paragraph(
            1,
            "Table cell text",
        )

        item = make_render_item(
            order=1,
            item_id="paragraph:1",
            kind=(
                RenderItemKind.PARAGRAPH
            ),
            source=paragraph,
            disposition=(
                RenderDisposition.SKIP
            ),
        )

        item.add_reason(
            "Paragraph is represented by table."
        )

        page.render_plan.add_item(
            item
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[
                make_layout_item(
                    paragraph
                )
            ],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            len(
                result.paragraph_instructions
            ),
            0,
        )

        self.assertEqual(
            result.instructions[0].action,
            EditableRenderAction.IGNORE,
        )

    def test_header_and_footer_are_not_body_paragraphs(
        self,
    ) -> None:
        page = make_page()

        header = make_paragraph(
            1,
            "Header",
        )

        footer = make_paragraph(
            2,
            "Footer",
        )

        page.render_plan.add_item(
            make_render_item(
                order=1,
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=header,
                placement=(
                    RenderPlacement.FLOATING
                ),
                role=(
                    RenderItemRole.HEADER
                ),
            )
        )

        page.render_plan.add_item(
            make_render_item(
                order=2,
                item_id="paragraph:2",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=footer,
                placement=(
                    RenderPlacement.FLOATING
                ),
                role=(
                    RenderItemRole.FOOTER
                ),
            )
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[
                make_layout_item(
                    header
                ),
                make_layout_item(
                    footer
                ),
            ],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            result.paragraph_instructions,
            [],
        )

        self.assertEqual(
            len(
                result.ignored_instructions
            ),
            2,
        )

    def test_table_image_and_chart_are_deferred(
        self,
    ) -> None:
        page = make_page()

        table = SimpleNamespace()
        image = SimpleNamespace()
        chart = SimpleNamespace()

        page.render_plan.add_item(
            make_render_item(
                order=1,
                item_id="table:1",
                kind=(
                    RenderItemKind.TABLE
                ),
                source=table,
            )
        )

        page.render_plan.add_item(
            make_render_item(
                order=2,
                item_id="image:1",
                kind=(
                    RenderItemKind.IMAGE
                ),
                source=image,
                disposition=(
                    RenderDisposition.VISUAL
                ),
            )
        )

        page.render_plan.add_item(
            make_render_item(
                order=3,
                item_id="chart:1",
                kind=(
                    RenderItemKind.CHART
                ),
                source=chart,
                disposition=(
                    RenderDisposition.VISUAL
                ),
            )
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            [
                instruction.action
                for instruction
                in result.deferred_instructions
            ],
            [
                EditableRenderAction.DEFER_TABLE,
                EditableRenderAction.DEFER_IMAGE,
                EditableRenderAction.DEFER_CHART,
            ],
        )

    def test_region_number_fallback_matches_layout_item(
        self,
    ) -> None:
        page = make_page()

        render_paragraph = (
            make_paragraph(
                7,
                "Rendered instance",
            )
        )

        layout_paragraph = (
            make_paragraph(
                7,
                "Layout instance",
            )
        )

        layout_item = make_layout_item(
            layout_paragraph
        )

        page.render_plan.add_item(
            make_render_item(
                order=1,
                item_id="paragraph:7",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=render_paragraph,
            )
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[
                layout_item
            ],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        instruction = (
            result.paragraph_instructions[0]
        )

        self.assertIs(
            instruction.layout_item,
            layout_item,
        )

    def test_missing_layout_metadata_is_ignored_safely(
        self,
    ) -> None:
        page = make_page()

        paragraph = make_paragraph(
            1,
            "Missing layout",
        )

        page.render_plan.add_item(
            make_render_item(
                order=1,
                item_id="paragraph:1",
                kind=(
                    RenderItemKind.PARAGRAPH
                ),
                source=paragraph,
            )
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            len(
                result.paragraph_instructions
            ),
            0,
        )

        self.assertEqual(
            len(
                result.warnings
            ),
            1,
        )

    def test_empty_render_plan_uses_legacy_fallback(
        self,
    ) -> None:
        page = make_page()

        paragraph = make_paragraph(
            1,
            "Legacy paragraph",
        )

        layout_item = make_layout_item(
            paragraph
        )

        with patch(
            (
                "src.exporter."
                "editable_page_render_resolver."
                "EditableLayoutResolver."
                "build_page_plan"
            ),
            return_value=[
                layout_item
            ],
        ):
            result = (
                EditablePageRenderResolver
                .build_page_plan(
                    page
                )
            )

        self.assertEqual(
            len(
                result.paragraph_instructions
            ),
            1,
        )

        self.assertIs(
            result.paragraph_instructions[0]
            .layout_item,
            layout_item,
        )

        self.assertTrue(
            result.warnings
        )


if __name__ == "__main__":
    unittest.main()