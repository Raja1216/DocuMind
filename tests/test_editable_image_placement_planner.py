from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.editable_image_placement_planner import (
    EditableImagePlacementPlanner,
)
from src.models.editable_image import (
    EditableImage,
    EditableImageAnchorPosition,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImageHorizontalAlignment,
    EditableImagePlacement,
    EditableImageRole,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


def make_image(
    *,
    bbox: Rectangle,
    image_id: str = "image:1:1",
    xref: int | None = None,
    opacity: float = 1.0,
) -> EditableImage:
    return EditableImage(
        page_number=1,
        image_id=image_id,
        bbox=bbox,
        extraction_mode=(
            EditableImageExtractionMode
            .PDF_XREF
        ),
        disposition=(
            EditableImageDisposition.NATIVE
        ),
        xref=xref,
        opacity=opacity,
        confidence=0.90,
    )


def make_paragraph(
    number: int,
    bbox: Rectangle,
):
    return SimpleNamespace(
        number=number,
        bbox=bbox,
        role="body",
        is_header=False,
        is_footer=False,
    )


def make_page(
    *,
    number: int = 1,
    images=None,
    paragraphs=None,
):
    return SimpleNamespace(
        number=number,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        editable_images=list(
            images
            or []
        ),
        paragraph_regions=list(
            paragraphs
            or []
        ),
        editable_tables=[],
    )


class EditableImagePlacementPlannerTests(
    unittest.TestCase
):

    def test_full_page_image_becomes_background(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=600.0,
                bottom=800.0,
            ),
        )

        page = make_page(
            images=[
                image
            ]
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.BACKGROUND,
        )

        self.assertEqual(
            image.placement,
            EditableImagePlacement
            .BACKGROUND,
        )

    def test_translucent_centered_image_becomes_watermark(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=150.0,
                top=200.0,
                right=450.0,
                bottom=600.0,
            ),
            opacity=0.40,
        )

        page = make_page(
            images=[
                image
            ],
            paragraphs=[
                make_paragraph(
                    1,
                    Rectangle(
                        left=180.0,
                        top=250.0,
                        right=420.0,
                        bottom=550.0,
                    ),
                )
            ],
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.WATERMARK,
        )

        self.assertEqual(
            image.placement,
            EditableImagePlacement
            .BACKGROUND,
        )

    def test_repeated_header_image_becomes_logo(
        self,
    ) -> None:
        first = make_image(
            image_id="image:1:1",
            xref=20,
            bbox=Rectangle(
                left=20.0,
                top=20.0,
                right=120.0,
                bottom=70.0,
            ),
        )

        second = make_image(
            image_id="image:2:1",
            xref=20,
            bbox=Rectangle(
                left=20.0,
                top=20.0,
                right=120.0,
                bottom=70.0,
            ),
        )

        second.page_number = 2

        document = SimpleNamespace(
            pages=[
                make_page(
                    number=1,
                    images=[
                        first
                    ],
                ),
                make_page(
                    number=2,
                    images=[
                        second
                    ],
                ),
            ]
        )

        EditableImagePlacementPlanner.plan_document(
            document
        )

        self.assertEqual(
            first.role,
            EditableImageRole.LOGO,
        )

        self.assertEqual(
            second.role,
            EditableImageRole.LOGO,
        )

        self.assertEqual(
            first.repeat_count,
            2,
        )

        self.assertEqual(
            first.placement,
            EditableImagePlacement.FLOATING,
        )

    def test_content_image_between_paragraphs_becomes_inline(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=50.0,
                top=150.0,
                right=550.0,
                bottom=300.0,
            ),
        )

        page = make_page(
            images=[
                image
            ],
            paragraphs=[
                make_paragraph(
                    1,
                    Rectangle(
                        left=50.0,
                        top=60.0,
                        right=550.0,
                        bottom=100.0,
                    ),
                ),
                make_paragraph(
                    2,
                    Rectangle(
                        left=50.0,
                        top=350.0,
                        right=550.0,
                        bottom=400.0,
                    ),
                ),
            ],
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.CONTENT,
        )

        self.assertEqual(
            image.placement,
            EditableImagePlacement.INLINE,
        )

        self.assertEqual(
            image.anchor_paragraph_region_number,
            2,
        )

        self.assertEqual(
            image.anchor_position,
            EditableImageAnchorPosition.BEFORE,
        )

    def test_side_by_side_image_becomes_floating(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=40.0,
                top=150.0,
                right=240.0,
                bottom=320.0,
            ),
        )

        page = make_page(
            images=[
                image
            ],
            paragraphs=[
                make_paragraph(
                    1,
                    Rectangle(
                        left=270.0,
                        top=160.0,
                        right=560.0,
                        bottom=310.0,
                    ),
                )
            ],
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.placement,
            EditableImagePlacement.FLOATING,
        )

    def test_image_overlapping_text_becomes_overlay(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=80.0,
                top=150.0,
                right=520.0,
                bottom=350.0,
            ),
        )

        page = make_page(
            images=[
                image
            ],
            paragraphs=[
                make_paragraph(
                    1,
                    Rectangle(
                        left=100.0,
                        top=180.0,
                        right=500.0,
                        bottom=320.0,
                    ),
                )
            ],
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.placement,
            EditableImagePlacement.OVERLAY,
        )

    def test_tiny_image_is_preserved_as_decoration(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=20.0,
                top=200.0,
                right=30.0,
                bottom=210.0,
            ),
        )

        page = make_page(
            images=[
                image
            ]
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.DECORATION,
        )

        self.assertNotEqual(
            image.disposition,
            EditableImageDisposition.SKIP,
        )

    def test_center_alignment_is_detected(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=150.0,
                top=200.0,
                right=450.0,
                bottom=300.0,
            ),
        )

        page = make_page(
            images=[
                image
            ]
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.horizontal_alignment,
            EditableImageHorizontalAlignment
            .CENTER,
        )

    def test_page_without_images_is_safe(
        self,
    ) -> None:
        page = make_page()

        result = (
            EditableImagePlacementPlanner
            .plan_page(
                page=page
            )
        )

        self.assertEqual(
            result,
            [],
        )

    def test_reanalysis_replaces_planner_state(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=600.0,
                bottom=800.0,
            ),
        )

        page = make_page(
            images=[
                image
            ]
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.BACKGROUND,
        )

        image.bbox = Rectangle(
            left=100.0,
            top=200.0,
            right=500.0,
            bottom=350.0,
        )

        EditableImagePlacementPlanner.plan_page(
            page=page
        )

        self.assertEqual(
            image.role,
            EditableImageRole.CONTENT,
        )

        planner_reasons = [
            reason
            for reason in image.reasons
            if reason.startswith(
                EditableImagePlacementPlanner
                .PLANNER_MESSAGE_PREFIX
            )
        ]

        self.assertEqual(
            len(planner_reasons),
            1,
        )


if __name__ == "__main__":
    unittest.main()