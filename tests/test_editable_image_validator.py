from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.editable_image_validator import (
    EditableImageValidator,
)
from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImagePayloadStatus,
    EditableImagePlacement,
)
from src.models.editable_image_validation import (
    EditableImageRenderDecision,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"normalized-test-payload"
)


def make_page(
    images=None,
):
    return SimpleNamespace(
        number=1,
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
        editable_image_validation_reports={},
    )


def make_image(
    **overrides,
) -> EditableImage:
    values = {
        "page_number": 1,
        "image_id": "image:1:1",
        "bbox": Rectangle(
            left=50.0,
            top=100.0,
            right=250.0,
            bottom=200.0,
        ),
        "extraction_mode": (
            EditableImageExtractionMode
            .DIRECT_BYTES
        ),
        "disposition": (
            EditableImageDisposition.NATIVE
        ),
        "placement": (
            EditableImagePlacement.INLINE
        ),
        "payload": PNG_BYTES,
        "payload_status": (
            EditableImagePayloadStatus.READY
        ),
        "payload_mime_type": "image/png",
        "extension": "png",
        "pixel_width": 400,
        "pixel_height": 200,
        "confidence": 0.95,
        "placement_confidence": 0.90,
        "payload_confidence": 0.95,
        "anchor_paragraph_region_number": 1,
    }

    values.update(
        overrides
    )

    return EditableImage(
        **values
    )


class EditableImageValidatorTests(
    unittest.TestCase
):

    def test_ready_inline_image_is_safe(
        self,
    ) -> None:
        image = make_image()

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(
                    [
                        image
                    ]
                ),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision
            .NATIVE_INLINE_SAFE,
        )

        self.assertGreaterEqual(
            report.native_confidence,
            0.65,
        )

    def test_ready_floating_image_is_safe(
        self,
    ) -> None:
        image = make_image(
            placement=(
                EditableImagePlacement.FLOATING
            ),
            anchor_paragraph_region_number=None,
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(
                    [
                        image
                    ]
                ),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision
            .NATIVE_FLOATING_SAFE,
        )

    def test_skip_disposition_is_skipped(
        self,
    ) -> None:
        image = make_image(
            disposition=(
                EditableImageDisposition.SKIP
            ),
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.SKIP,
        )

    def test_missing_payload_is_deferred(
        self,
    ) -> None:
        image = make_image(
            payload=None,
            payload_status=(
                EditableImagePayloadStatus.FAILED
            ),
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_non_png_payload_is_deferred(
        self,
    ) -> None:
        image = make_image(
            payload=b"not-png",
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_rotated_image_is_deferred(
        self,
    ) -> None:
        image = make_image(
            rotation=90.0,
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_background_image_is_deferred(
        self,
    ) -> None:
        image = make_image(
            placement=(
                EditableImagePlacement.BACKGROUND
            ),
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_overlay_image_is_deferred(
        self,
    ) -> None:
        image = make_image(
            placement=(
                EditableImagePlacement.OVERLAY
            ),
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_oversized_image_is_deferred(
        self,
    ) -> None:
        image = make_image(
            pixel_width=20_000,
            pixel_height=20_000,
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_invalid_geometry_is_skipped(
        self,
    ) -> None:
        image = make_image(
            bbox=Rectangle(
                left=50.0,
                top=100.0,
                right=50.0,
                bottom=200.0,
            ),
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.SKIP,
        )

    def test_low_placement_confidence_is_deferred(
        self,
    ) -> None:
        image = make_image(
            placement_confidence=0.10,
        )

        report = (
            EditableImageValidator
            .validate_image(
                page=make_page(),
                image=image,
            )
        )

        self.assertEqual(
            report.decision,
            EditableImageRenderDecision.DEFER,
        )

    def test_page_validation_replaces_stale_reports(
        self,
    ) -> None:
        image = make_image()

        page = make_page(
            [
                image
            ]
        )

        page.editable_image_validation_reports = {
            "stale": "stale"
        }

        reports = (
            EditableImageValidator
            .validate_page(
                page
            )
        )

        self.assertEqual(
            set(
                reports
            ),
            {
                image.image_id
            },
        )

        self.assertEqual(
            page.editable_image_validation_reports,
            reports,
        )

    def test_page_without_images_clears_reports(
        self,
    ) -> None:
        page = make_page()

        page.editable_image_validation_reports = {
            "stale": "stale"
        }

        reports = (
            EditableImageValidator
            .validate_page(
                page
            )
        )

        self.assertEqual(
            reports,
            {},
        )

        self.assertEqual(
            page.editable_image_validation_reports,
            {},
        )


if __name__ == "__main__":
    unittest.main()