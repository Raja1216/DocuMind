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
from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImagePayloadStatus,
    EditableImagePlacement,
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
        editable_images=[],
        editable_tables=[],
        editable_table_validation_reports={},
    )

def make_editable_image(
    *,
    order: int,
    source_image,
    placement: EditableImagePlacement = (
        EditableImagePlacement.INLINE
    ),
    disposition: EditableImageDisposition = (
        EditableImageDisposition.NATIVE
    ),
    payload_status: EditableImagePayloadStatus = (
        EditableImagePayloadStatus.READY
    ),
    payload: bytes | None = b"resolved-payload",
    xref: int | None = None,
    rotation: float = 0.0,
) -> EditableImage:
    return EditableImage(
        page_number=1,
        image_id=(
            f"image:1:{order}"
        ),
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
        source_image=source_image,
        extraction_mode=(
            EditableImageExtractionMode
            .DIRECT_BYTES
        ),
        disposition=disposition,
        placement=placement,
        payload=payload,
        payload_status=payload_status,
        payload_mime_type="image/png",
        extension="png",
        xref=xref,
        confidence=0.95,
        payload_confidence=0.95,
        rotation=rotation,
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

def test_ready_inline_image_is_rendered(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace(
        xref=20
    )

    editable_image = make_editable_image(
        order=1,
        source_image=source_image,
        xref=20,
    )

    page.editable_images = [
        editable_image
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
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
            result.inline_image_instructions
        ),
        1,
    )

    self.assertEqual(
        result.instructions[0].action,
        EditableRenderAction
        .RENDER_INLINE_IMAGE,
    )

    self.assertIs(
        result.instructions[0].source,
        editable_image,
    )


def test_region_rendered_inline_image_is_rendered(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    editable_image = make_editable_image(
        order=1,
        source_image=source_image,
        disposition=(
            EditableImageDisposition
            .REGION_FALLBACK
        ),
        payload_status=(
            EditableImagePayloadStatus
            .REGION_RENDERED
        ),
    )

    page.editable_images = [
        editable_image
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
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
        result.instructions[0].action,
        EditableRenderAction
        .RENDER_INLINE_IMAGE,
    )


def test_floating_image_remains_deferred(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    page.editable_images = [
        make_editable_image(
            order=1,
            source_image=source_image,
            placement=(
                EditableImagePlacement.FLOATING
            ),
        )
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
            placement=(
                RenderPlacement.FLOATING
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
        result.instructions[0].action,
        EditableRenderAction.DEFER_IMAGE,
    )


def test_background_image_remains_deferred(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    page.editable_images = [
        make_editable_image(
            order=1,
            source_image=source_image,
            placement=(
                EditableImagePlacement
                .BACKGROUND
            ),
        )
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
            placement=(
                RenderPlacement.BACKGROUND
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
        result.instructions[0].action,
        EditableRenderAction.DEFER_IMAGE,
    )


def test_overlay_image_remains_deferred(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    page.editable_images = [
        make_editable_image(
            order=1,
            source_image=source_image,
            placement=(
                EditableImagePlacement.OVERLAY
            ),
        )
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
            placement=(
                RenderPlacement.OVERLAY
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
        result.instructions[0].action,
        EditableRenderAction.DEFER_IMAGE,
    )


def test_missing_image_payload_remains_deferred(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    page.editable_images = [
        make_editable_image(
            order=1,
            source_image=source_image,
            payload=None,
            payload_status=(
                EditableImagePayloadStatus.FAILED
            ),
        )
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
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
        result.instructions[0].action,
        EditableRenderAction.DEFER_IMAGE,
    )


def test_skipped_image_is_ignored(
    self,
) -> None:
    page = make_page()

    source_image = SimpleNamespace()

    page.editable_images = [
        make_editable_image(
            order=1,
            source_image=source_image,
            disposition=(
                EditableImageDisposition.SKIP
            ),
        )
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=source_image,
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
        result.instructions[0].action,
        EditableRenderAction.IGNORE,
    )


def test_repeated_xref_placements_match_independently(
    self,
) -> None:
    page = make_page()

    first_source = SimpleNamespace(
        xref=50
    )

    second_source = SimpleNamespace(
        xref=50
    )

    first_image = make_editable_image(
        order=1,
        source_image=first_source,
        xref=50,
    )

    second_image = make_editable_image(
        order=2,
        source_image=second_source,
        xref=50,
    )

    page.editable_images = [
        first_image,
        second_image,
    ]

    page.render_plan.add_item(
        make_render_item(
            order=1,
            item_id="image:1",
            kind=RenderItemKind.IMAGE,
            source=first_source,
        )
    )

    page.render_plan.add_item(
        make_render_item(
            order=2,
            item_id="image:2",
            kind=RenderItemKind.IMAGE,
            source=second_source,
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
            result.inline_image_instructions
        ),
        2,
    )

    self.assertIs(
        result.instructions[0].source,
        first_image,
    )

    self.assertIs(
        result.instructions[1].source,
        second_image,
    )

if __name__ == "__main__":
    unittest.main()