from __future__ import annotations

import base64
import unittest

from types import SimpleNamespace

from src.analyzer.editable_image_payload_extractor import (
    EditableImagePayloadExtractor,
)
from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImagePayloadStatus,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


PNG_BYTES = base64.b64decode(
    (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
        "CAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAusB9Y9Z5ZkAAAAASUVORK5CYII="
    )
)


class FakeDocument:
    def __init__(
        self,
        images=None,
    ) -> None:
        self.images = dict(
            images
            or {}
        )

        self.extract_calls = []

    def extract_image(
        self,
        xref,
    ):
        self.extract_calls.append(
            xref
        )

        value = self.images.get(
            xref
        )

        if isinstance(
            value,
            Exception,
        ):
            raise value

        if value is None:
            raise ValueError(
                "Unknown xref"
            )

        return value


class FakePage:
    def __init__(
        self,
        payload=PNG_BYTES,
    ) -> None:
        self.payload = payload

        self.calls = []

    def render_region(
        self,
        *,
        bbox,
        dpi,
    ):
        self.calls.append(
            (
                bbox,
                dpi,
            )
        )

        return self.payload


def make_image(
    *,
    extraction_mode=(
        EditableImageExtractionMode
        .DIRECT_BYTES
    ),
    payload=PNG_BYTES,
    xref=None,
    soft_mask_xref=None,
    disposition=(
        EditableImageDisposition.NATIVE
    ),
):
    return EditableImage(
        page_number=1,
        image_id="image:1:1",
        bbox=Rectangle(
            left=10.0,
            top=20.0,
            right=210.0,
            bottom=120.0,
        ),
        extraction_mode=(
            extraction_mode
        ),
        disposition=disposition,
        payload=payload,
        xref=xref,
        soft_mask_xref=(
            soft_mask_xref
        ),
        confidence=0.90,
    )


class EditableImagePayloadExtractorTests(
    unittest.TestCase
):

    def test_direct_bytes_become_ready_png(
        self,
    ) -> None:
        image = make_image()

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=None,
            editable_images=[
                image
            ],
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.READY,
        )

        self.assertEqual(
            image.extension,
            "png",
        )

        self.assertEqual(
            image.payload_mime_type,
            "image/png",
        )

        self.assertTrue(
            image.has_resolved_payload
        )

    def test_xref_payload_is_extracted(
        self,
    ) -> None:
        source_document = FakeDocument(
            images={
                20: {
                    "image": PNG_BYTES,
                    "ext": "png",
                    "width": 1,
                    "height": 1,
                    "smask": 0,
                }
            }
        )

        image = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PDF_XREF
            ),
            payload=None,
            xref=20,
        )

        document = SimpleNamespace(
            source_pdf_document=(
                source_document
            ),
        )

        page = SimpleNamespace(
            source_pdf_page=None,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.READY,
        )

        self.assertEqual(
            source_document.extract_calls,
            [
                20
            ],
        )

    def test_soft_mask_is_composed(
        self,
    ) -> None:
        source_document = FakeDocument(
            images={
                20: {
                    "image": PNG_BYTES,
                    "ext": "png",
                    "smask": 21,
                },
                21: {
                    "image": PNG_BYTES,
                    "ext": "png",
                    "smask": 0,
                },
            }
        )

        image = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PDF_XREF
            ),
            payload=None,
            xref=20,
            soft_mask_xref=21,
        )

        document = SimpleNamespace(
            source_pdf_document=(
                source_document
            ),
        )

        page = SimpleNamespace(
            source_pdf_page=None,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.READY,
        )

        self.assertTrue(
            image.used_soft_mask
        )

        self.assertTrue(
            image.has_alpha
        )

    def test_page_region_is_rendered(
        self,
    ) -> None:
        image = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PAGE_REGION
            ),
            payload=None,
        )

        source_page = FakePage()

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=source_page,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus
            .REGION_RENDERED,
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition
            .REGION_FALLBACK,
        )

        self.assertEqual(
            len(
                source_page.calls
            ),
            1,
        )

    def test_invalid_direct_bytes_fall_back_to_region(
        self,
    ) -> None:
        image = make_image(
            payload=b"not-an-image",
        )

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=FakePage(),
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus
            .REGION_RENDERED,
        )

        self.assertTrue(
            image.warnings
        )

    def test_xref_failure_falls_back_to_region(
        self,
    ) -> None:
        image = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PDF_XREF
            ),
            payload=None,
            xref=99,
        )

        document = SimpleNamespace(
            source_pdf_document=(
                FakeDocument()
            ),
        )

        page = SimpleNamespace(
            source_pdf_page=FakePage(),
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus
            .REGION_RENDERED,
        )

    def test_missing_all_sources_fails_safely(
        self,
    ) -> None:
        image = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .UNAVAILABLE
            ),
            payload=None,
        )

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=None,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.FAILED,
        )

        self.assertEqual(
            image.disposition,
            EditableImageDisposition.SKIP,
        )

        self.assertIsNotNone(
            image.payload_error
        )

    def test_skip_disposition_remains_skipped(
        self,
    ) -> None:
        image = make_image(
            disposition=(
                EditableImageDisposition.SKIP
            ),
        )

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=None,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.SKIPPED,
        )

    def test_repeated_xref_uses_cache(
        self,
    ) -> None:
        source_document = FakeDocument(
            images={
                20: {
                    "image": PNG_BYTES,
                    "ext": "png",
                    "smask": 0,
                }
            }
        )

        first = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PDF_XREF
            ),
            payload=None,
            xref=20,
        )

        second = make_image(
            extraction_mode=(
                EditableImageExtractionMode
                .PDF_XREF
            ),
            payload=None,
            xref=20,
        )

        second.image_id = "image:1:2"

        document = SimpleNamespace(
            source_pdf_document=(
                source_document
            ),
        )

        page = SimpleNamespace(
            source_pdf_page=None,
            editable_images=[
                first,
                second,
            ],
        )

        EditableImagePayloadExtractor.extract_page(
            document=document,
            page=page,
        )

        self.assertEqual(
            source_document.extract_calls,
            [
                20
            ],
        )

        self.assertTrue(
            first.has_resolved_payload
        )

        self.assertTrue(
            second.has_resolved_payload
        )

    def test_page_without_images_is_safe(
        self,
    ) -> None:
        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=None,
            editable_images=[],
        )

        result = (
            EditableImagePayloadExtractor
            .extract_page(
                document=document,
                page=page,
            )
        )

        self.assertEqual(
            result,
            [],
        )

    def test_reanalysis_replaces_stale_error(
        self,
    ) -> None:
        image = make_image()

        image.payload_status = (
            EditableImagePayloadStatus.FAILED
        )

        image.payload_error = (
            "stale error"
        )

        image.warnings.append(
            (
                EditableImagePayloadExtractor
                .MESSAGE_PREFIX
                + "stale warning"
            )
        )

        document = SimpleNamespace(
            source_pdf_document=None,
        )

        page = SimpleNamespace(
            source_pdf_page=None,
        )

        EditableImagePayloadExtractor.extract_image(
            document=document,
            page=page,
            image=image,
        )

        self.assertEqual(
            image.payload_status,
            EditableImagePayloadStatus.READY,
        )

        self.assertIsNone(
            image.payload_error
        )

        payload_warnings = [
            warning
            for warning in image.warnings
            if warning.startswith(
                EditableImagePayloadExtractor
                .MESSAGE_PREFIX
            )
        ]

        self.assertEqual(
            payload_warnings,
            [],
        )


if __name__ == "__main__":
    unittest.main()