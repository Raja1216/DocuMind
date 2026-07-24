from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.editable_image_normalizer import (
    EditableImageNormalizer,
)
from src.models.editable_image import (
    EditableImageDisposition,
    EditableImageExtractionMode,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


def make_page(
    *,
    source_pdf_page=object(),
):
    return SimpleNamespace(
        number=1,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        images=[],
        editable_images=[],
        source_pdf_page=(
            source_pdf_page
        ),
    )


def make_source_image(
    **overrides,
):
    values = {
        "bbox": Rectangle(
            left=10.0,
            top=20.0,
            right=210.0,
            bottom=120.0,
        ),
        "pixel_width": 400,
        "pixel_height": 200,
        "extension": "png",
    }

    values.update(
        overrides
    )

    return SimpleNamespace(
        **values
    )


class EditableImageNormalizerTests(
    unittest.TestCase
):

    def test_direct_payload_is_detected(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            payload=b"image-data",
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.extraction_mode,
            EditableImageExtractionMode
            .DIRECT_BYTES,
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition
            .NATIVE,
        )

    def test_valid_xref_is_detected(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            xref=42,
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.extraction_mode,
            EditableImageExtractionMode
            .PDF_XREF,
        )

    def test_page_region_fallback_is_detected(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image()

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.extraction_mode,
            EditableImageExtractionMode
            .PAGE_REGION,
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition
            .REGION_FALLBACK,
        )

    def test_missing_extraction_source_is_skipped(
        self,
    ) -> None:
        page = make_page(
            source_pdf_page=None,
        )

        source = make_source_image()

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition.SKIP,
        )

    def test_partially_outside_image_is_clipped(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            bbox=Rectangle(
                left=-20.0,
                top=10.0,
                right=200.0,
                bottom=100.0,
            ),
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.bbox.left,
            0.0,
        )

        self.assertTrue(
            image.warnings
        )

    def test_fully_outside_image_is_skipped(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            bbox=Rectangle(
                left=700.0,
                top=900.0,
                right=800.0,
                bottom=1000.0,
            ),
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition.SKIP,
        )

    def test_zero_area_image_is_skipped(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            bbox=Rectangle(
                left=10.0,
                top=20.0,
                right=10.0,
                bottom=100.0,
            ),
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition.SKIP,
        )

    def test_same_xref_creates_separate_placements(
        self,
    ) -> None:
        page = make_page()

        page.images = [
            make_source_image(
                xref=42,
                bbox=Rectangle(
                    left=10.0,
                    top=20.0,
                    right=110.0,
                    bottom=120.0,
                ),
            ),
            make_source_image(
                xref=42,
                bbox=Rectangle(
                    left=200.0,
                    top=20.0,
                    right=300.0,
                    bottom=120.0,
                ),
            ),
        ]

        images = (
            EditableImageNormalizer
            .normalize_page(
                page
            )
        )

        self.assertEqual(
            len(images),
            2,
        )

        self.assertNotEqual(
            images[0].image_id,
            images[1].image_id,
        )

        self.assertEqual(
            images[0].xref,
            images[1].xref,
        )

    def test_soft_mask_and_alpha_are_preserved(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            xref=42,
            smask=43,
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.soft_mask_xref,
            43,
        )

        self.assertTrue(
            image.has_alpha
        )

    def test_pixel_dimensions_and_extension_are_preserved(
        self,
    ) -> None:
        page = make_page()

        source = make_source_image(
            payload=b"data",
            pixel_width=1200,
            pixel_height=800,
            extension="JPG",
        )

        image = (
            EditableImageNormalizer
            .normalize_image(
                page=page,
                source_image=source,
                image_index=0,
            )
        )

        self.assertEqual(
            image.pixel_width,
            1200,
        )

        self.assertEqual(
            image.pixel_height,
            800,
        )

        self.assertEqual(
            image.extension,
            "jpeg",
        )

    def test_reanalysis_replaces_stale_images(
        self,
    ) -> None:
        page = make_page()

        page.editable_images = [
            "stale-image"
        ]

        page.images = [
            make_source_image(
                payload=b"one",
            )
        ]

        first = (
            EditableImageNormalizer
            .normalize_page(
                page
            )
        )

        self.assertEqual(
            len(first),
            1,
        )

        page.images = [
            make_source_image(
                payload=b"two",
            ),
            make_source_image(
                payload=b"three",
            ),
        ]

        second = (
            EditableImageNormalizer
            .normalize_page(
                page
            )
        )

        self.assertEqual(
            len(second),
            2,
        )

        self.assertEqual(
            page.editable_images,
            second,
        )

    def test_page_without_images_clears_stale_models(
        self,
    ) -> None:
        page = make_page()

        page.editable_images = [
            "stale-image"
        ]

        page.images = []

        images = (
            EditableImageNormalizer
            .normalize_page(
                page
            )
        )

        self.assertEqual(
            images,
            [],
        )

        self.assertEqual(
            page.editable_images,
            [],
        )


if __name__ == "__main__":
    unittest.main()