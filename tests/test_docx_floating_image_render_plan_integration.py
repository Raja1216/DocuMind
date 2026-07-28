from __future__ import annotations

import unittest

from types import SimpleNamespace
from unittest.mock import patch

from docx import Document
from docx.oxml.ns import qn

from src.exporter.docx_exporter import (
    DocxExporter,
)
from src.exporter.editable_page_render_resolver import (
    EditablePageRenderPlan,
    EditableRenderAction,
    EditableRenderInstruction,
)
from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImagePayloadStatus,
    EditableImagePlacement,
    EditableImageRole,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page_render_plan import (
    PageRenderItem,
    RenderDisposition,
    RenderItemKind,
    RenderItemRole,
    RenderPlacement,
)


def create_test_png() -> bytes:
    try:
        import pymupdf

    except ImportError:
        import fitz as pymupdf

    pixmap = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(
            0,
            0,
            4,
            2,
        ),
        False,
    )

    pixmap.clear_with(
        255
    )

    return pixmap.tobytes(
        "png"
    )


PNG_BYTES = create_test_png()


def make_image(
    *,
    image_id: str = "image:1:1",
    bbox: Rectangle | None = None,
    payload: bytes = PNG_BYTES,
) -> EditableImage:
    return EditableImage(
        page_number=1,
        image_id=image_id,
        bbox=(
            bbox
            or Rectangle(
                left=72.0,
                top=144.0,
                right=272.0,
                bottom=244.0,
            )
        ),
        extraction_mode=(
            EditableImageExtractionMode
            .DIRECT_BYTES
        ),
        disposition=(
            EditableImageDisposition.NATIVE
        ),
        placement=(
            EditableImagePlacement.FLOATING
        ),
        role=EditableImageRole.CONTENT,
        payload=payload,
        payload_status=(
            EditableImagePayloadStatus.READY
        ),
        payload_mime_type="image/png",
        extension="png",
        confidence=0.95,
        payload_confidence=0.95,
    )


def make_render_item(
    image: EditableImage,
    *,
    order: int,
) -> PageRenderItem:
    return PageRenderItem(
        order=order,
        page_number=1,
        item_id=(
            f"image:{order}"
        ),
        kind=RenderItemKind.IMAGE,
        placement=(
            RenderPlacement.FLOATING
        ),
        disposition=(
            RenderDisposition.VISUAL
        ),
        role=RenderItemRole.BODY,
        bbox=image.bbox,
        source=image,
        source_index=order - 1,
        confidence=0.95,
    )


def make_floating_instruction(
    image: EditableImage,
    *,
    order: int,
) -> EditableRenderInstruction:
    return EditableRenderInstruction(
        order=order,
        action=(
            EditableRenderAction
            .RENDER_FLOATING_IMAGE
        ),
        source=image,
        render_item=(
            make_render_item(
                image,
                order=order,
            )
        ),
    )


def make_page():
    return SimpleNamespace(
        number=1,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        profile=None,
        editable_table_export_results={},
        editable_table_validation_reports={},
    )


class FloatingImageRenderPlanIntegrationTests(
    unittest.TestCase
):

    def render_plan(
        self,
        plan,
    ):
        document = Document()

        with patch.object(
            DocxExporter,
            "_build_editable_render_plan",
            return_value=plan,
        ):
            DocxExporter._render_page(
                word_document=document,
                page=make_page(),
                numbering_manager=(
                    SimpleNamespace()
                ),
                list_sequence_resolver=(
                    SimpleNamespace()
                ),
                validation_report=None,
            )

        return document

    def test_floating_image_creates_word_anchor(
        self,
    ) -> None:
        image = make_image()

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                make_floating_instruction(
                    image,
                    order=1,
                )
            ],
        )

        document = self.render_plan(
            plan
        )

        body_xml = (
            document._element.body.xml
        )

        self.assertIn(
            "wp:anchor",
            body_xml,
        )

        self.assertNotIn(
            "wp:inline",
            body_xml,
        )

    def test_floating_image_only_page_is_rendered(
        self,
    ) -> None:
        image = make_image()

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                make_floating_instruction(
                    image,
                    order=1,
                )
            ],
        )

        document = self.render_plan(
            plan
        )

        anchors = list(
            document._element.body.iter(
                qn(
                    "wp:anchor"
                )
            )
        )

        self.assertEqual(
            len(
                anchors
            ),
            1,
        )

    def test_page_relative_offsets_are_preserved(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=72.0,
                top=144.0,
                right=272.0,
                bottom=244.0,
            )
        )

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                make_floating_instruction(
                    image,
                    order=1,
                )
            ],
        )

        document = self.render_plan(
            plan
        )

        anchor = next(
            document._element.body.iter(
                qn(
                    "wp:anchor"
                )
            )
        )

        horizontal_position = (
            anchor.find(
                qn(
                    "wp:positionH"
                )
            )
        )

        vertical_position = (
            anchor.find(
                qn(
                    "wp:positionV"
                )
            )
        )

        horizontal_offset = (
            horizontal_position.find(
                qn(
                    "wp:posOffset"
                )
            )
        )

        vertical_offset = (
            vertical_position.find(
                qn(
                    "wp:posOffset"
                )
            )
        )

        self.assertEqual(
            horizontal_offset.text,
            str(
                int(
                    72.0
                    * 12_700
                )
            ),
        )

        self.assertEqual(
            vertical_offset.text,
            str(
                int(
                    144.0
                    * 12_700
                )
            ),
        )

    def test_two_floating_placements_are_independent(
        self,
    ) -> None:
        first = make_image(
            image_id="image:1:1",
            bbox=Rectangle(
                left=20.0,
                top=20.0,
                right=120.0,
                bottom=70.0,
            ),
        )

        second = make_image(
            image_id="image:1:2",
            bbox=Rectangle(
                left=300.0,
                top=200.0,
                right=500.0,
                bottom=300.0,
            ),
        )

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                make_floating_instruction(
                    first,
                    order=1,
                ),
                make_floating_instruction(
                    second,
                    order=2,
                ),
            ],
        )

        document = self.render_plan(
            plan
        )

        anchors = list(
            document._element.body.iter(
                qn(
                    "wp:anchor"
                )
            )
        )

        self.assertEqual(
            len(
                anchors
            ),
            2,
        )

    def test_invalid_floating_image_is_rolled_back(
        self,
    ) -> None:
        image = make_image(
            payload=b"invalid-image"
        )

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                make_floating_instruction(
                    image,
                    order=1,
                )
            ],
        )

        document = self.render_plan(
            plan
        )

        self.assertNotIn(
            "wp:anchor",
            document._element.body.xml,
        )

        self.assertTrue(
            any(
                warning.startswith(
                    "[floating-export]"
                )
                for warning
                in image.warnings
            )
        )

    def test_deferred_background_image_is_absent(
        self,
    ) -> None:
        image = make_image()

        image.placement = (
            EditableImagePlacement.BACKGROUND
        )

        plan = EditablePageRenderPlan(
            page_number=1,
            instructions=[
                EditableRenderInstruction(
                    order=1,
                    action=(
                        EditableRenderAction
                        .DEFER_IMAGE
                    ),
                    source=image,
                )
            ],
        )

        document = self.render_plan(
            plan
        )

        self.assertNotIn(
            "wp:anchor",
            document._element.body.xml,
        )


if __name__ == "__main__":
    unittest.main()