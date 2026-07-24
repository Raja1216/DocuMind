from __future__ import annotations

import unittest

from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableImageModelTests(
    unittest.TestCase
):

    def make_image(
        self,
        **overrides,
    ) -> EditableImage:
        values = {
            "page_number": 1,
            "image_id": "image:1:1",
            "bbox": Rectangle(
                left=10.0,
                top=20.0,
                right=210.0,
                bottom=120.0,
            ),
            "extraction_mode": (
                EditableImageExtractionMode
                .DIRECT_BYTES
            ),
            "disposition": (
                EditableImageDisposition
                .NATIVE
            ),
            "payload": b"test",
            "extension": "png",
            "pixel_width": 400,
            "pixel_height": 200,
            "confidence": 0.90,
        }

        values.update(
            overrides
        )

        return EditableImage(
            **values
        )

    def test_valid_model_creation(
        self,
    ) -> None:
        image = self.make_image()

        self.assertEqual(
            image.width,
            200.0,
        )

        self.assertEqual(
            image.height,
            100.0,
        )

        self.assertTrue(
            image.can_extract
        )

    def test_empty_image_id_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            self.make_image(
                image_id="",
            )

    def test_invalid_page_number_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            self.make_image(
                page_number=0,
            )

    def test_rotation_is_normalized(
        self,
    ) -> None:
        image = self.make_image(
            rotation=450.0,
        )

        self.assertEqual(
            image.rotation,
            90.0,
        )

    def test_confidence_is_clamped(
        self,
    ) -> None:
        image = self.make_image(
            confidence=5.0,
        )

        self.assertEqual(
            image.confidence,
            1.0,
        )

    def test_extension_alias_is_normalized(
        self,
    ) -> None:
        image = self.make_image(
            extension=".JPG",
        )

        self.assertEqual(
            image.extension,
            "jpeg",
        )

    def test_aspect_ratios_are_calculated(
        self,
    ) -> None:
        image = self.make_image()

        self.assertEqual(
            image.aspect_ratio,
            2.0,
        )

        self.assertEqual(
            image.pixel_aspect_ratio,
            2.0,
        )

    def test_unavailable_image_cannot_extract(
        self,
    ) -> None:
        image = self.make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .UNAVAILABLE
            ),
            payload=None,
        )

        self.assertFalse(
            image.can_extract
        )


if __name__ == "__main__":
    unittest.main()