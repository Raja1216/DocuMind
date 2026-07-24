from __future__ import annotations

import hashlib
import math

from typing import Any

from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    EditableImagePayloadStatus,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableImagePayloadExtractor:
    """
    Resolve reliable PNG payloads for normalized image placements.

    Extraction order:

    1. Direct embedded bytes.
    2. PDF xref extraction.
    3. Source-page region rendering.
    4. Failure without stopping document analysis.

    All output payloads are normalized to PNG so that later Word
    rendering receives one predictable image format.
    """

    DEFAULT_REGION_DPI = 200

    MINIMUM_REGION_DPI = 96

    MAXIMUM_REGION_DPI = 400

    MAXIMUM_PIXEL_COUNT = 40_000_000

    MAXIMUM_PIXEL_DIMENSION = 12_000

    MESSAGE_PREFIX = (
        "[image-payload] "
    )

    @classmethod
    def extract_document(
        cls,
        document,
    ) -> None:
        payload_cache: dict[
            tuple[Any, ...],
            dict[str, Any],
        ] = {}

        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.extract_page(
                document=document,
                page=page,
                payload_cache=payload_cache,
            )

    @classmethod
    def extract_page(
        cls,
        *,
        document,
        page,
        payload_cache: dict[
            tuple[Any, ...],
            dict[str, Any],
        ] | None = None,
    ) -> list[EditableImage]:
        if payload_cache is None:
            payload_cache = {}

        images = list(
            getattr(
                page,
                "editable_images",
                [],
            )
            or []
        )

        for image in images:
            cls.extract_image(
                document=document,
                page=page,
                image=image,
                payload_cache=payload_cache,
            )

        return images

    @classmethod
    def extract_image(
        cls,
        *,
        document,
        page,
        image: EditableImage,
        payload_cache: dict[
            tuple[Any, ...],
            dict[str, Any],
        ] | None = None,
    ) -> EditableImage:
        if payload_cache is None:
            payload_cache = {}

        cls._reset_payload_state(
            image
        )

        if (
            image.disposition
            == EditableImageDisposition.SKIP
            or not image.has_valid_geometry
        ):
            image.payload = None

            image.payload_status = (
                EditableImagePayloadStatus
                .SKIPPED
            )

            image.add_warning(
                cls.MESSAGE_PREFIX
                + (
                    "Image payload extraction was "
                    "skipped because the placement "
                    "is not renderable."
                )
            )

            return image

        source_document = getattr(
            document,
            "source_pdf_document",
            None,
        )

        source_page = getattr(
            page,
            "source_pdf_page",
            None,
        )

        extraction_errors: list[str] = []

        # -----------------------------------------------------
        # 1. Direct image bytes
        # -----------------------------------------------------

        if (
            image.extraction_mode
            == EditableImageExtractionMode
            .DIRECT_BYTES
            and image.payload
        ):
            cache_key = (
                "direct",
                hashlib.sha256(
                    image.payload
                ).hexdigest(),
            )

            try:
                payload_result = (
                    payload_cache.get(
                        cache_key
                    )
                )

                if payload_result is None:
                    payload_result = (
                        cls._normalize_image_bytes(
                            image.payload
                        )
                    )

                    payload_cache[
                        cache_key
                    ] = payload_result

                cls._apply_payload_result(
                    image=image,
                    payload_result=(
                        payload_result
                    ),
                    payload_status=(
                        EditableImagePayloadStatus
                        .READY
                    ),
                    payload_confidence=0.96,
                )

                image.add_reason(
                    cls.MESSAGE_PREFIX
                    + (
                        "Direct source bytes were "
                        "validated and normalized."
                    )
                )

                return image

            except Exception as error:
                extraction_errors.append(
                    (
                        "Direct image-byte extraction "
                        f"failed: {error}"
                    )
                )

        # -----------------------------------------------------
        # 2. PDF xref
        # -----------------------------------------------------

        if (
            image.xref is not None
            and source_document is not None
        ):
            cache_key = (
                "xref",
                id(
                    source_document
                ),
                image.xref,
                image.soft_mask_xref,
            )

            try:
                payload_result = (
                    payload_cache.get(
                        cache_key
                    )
                )

                if payload_result is None:
                    payload_result = (
                        cls._extract_xref_payload(
                            source_document=(
                                source_document
                            ),
                            xref=image.xref,
                            soft_mask_xref=(
                                image
                                .soft_mask_xref
                            ),
                        )
                    )

                    payload_cache[
                        cache_key
                    ] = payload_result

                cls._apply_payload_result(
                    image=image,
                    payload_result=(
                        payload_result
                    ),
                    payload_status=(
                        EditableImagePayloadStatus
                        .READY
                    ),
                    payload_confidence=0.94,
                )

                image.extraction_mode = (
                    EditableImageExtractionMode
                    .PDF_XREF
                )

                image.add_reason(
                    cls.MESSAGE_PREFIX
                    + (
                        "Image bytes were extracted "
                        "from the source PDF xref."
                    )
                )

                return image

            except Exception as error:
                extraction_errors.append(
                    (
                        "PDF xref extraction failed: "
                        f"{error}"
                    )
                )

        # -----------------------------------------------------
        # 3. Source-page region rendering
        # -----------------------------------------------------

        if source_page is not None:
            try:
                payload_result = (
                    cls._render_page_region(
                        source_page=source_page,
                        bbox=image.bbox,
                        dpi=(
                            cls.DEFAULT_REGION_DPI
                        ),
                    )
                )

                cls._apply_payload_result(
                    image=image,
                    payload_result=(
                        payload_result
                    ),
                    payload_status=(
                        EditableImagePayloadStatus
                        .REGION_RENDERED
                    ),
                    payload_confidence=0.78,
                )

                image.extraction_mode = (
                    EditableImageExtractionMode
                    .PAGE_REGION
                )

                image.disposition = (
                    EditableImageDisposition
                    .REGION_FALLBACK
                )

                image.add_reason(
                    cls.MESSAGE_PREFIX
                    + (
                        "Image payload was rendered "
                        "from its source-page region."
                    )
                )

                for message in extraction_errors:
                    image.add_warning(
                        cls.MESSAGE_PREFIX
                        + message
                    )

                return image

            except Exception as error:
                extraction_errors.append(
                    (
                        "Source-page region rendering "
                        f"failed: {error}"
                    )
                )

        # -----------------------------------------------------
        # 4. Final failure
        # -----------------------------------------------------

        image.payload = None

        image.payload_status = (
            EditableImagePayloadStatus.FAILED
        )

        image.payload_confidence = 0.0

        image.payload_error = (
            "; ".join(
                extraction_errors
            )
            or (
                "No direct bytes, PDF xref, "
                "or source-page region was "
                "available."
            )
        )

        image.disposition = (
            EditableImageDisposition.SKIP
        )

        image.add_warning(
            cls.MESSAGE_PREFIX
            + image.payload_error
        )

        return image

    # ---------------------------------------------------------
    # Direct byte normalization
    # ---------------------------------------------------------

    @classmethod
    def _normalize_image_bytes(
        cls,
        payload: bytes,
    ) -> dict[str, Any]:
        pymupdf = cls._load_pymupdf()

        if not payload:
            raise ValueError(
                "Image payload is empty."
            )

        pixmap = pymupdf.Pixmap(
            payload
        )

        return cls._pixmap_to_payload_result(
            pixmap=pixmap,
            pymupdf=pymupdf,
            used_soft_mask=False,
        )

    # ---------------------------------------------------------
    # PDF xref extraction
    # ---------------------------------------------------------

    @classmethod
    def _extract_xref_payload(
        cls,
        *,
        source_document,
        xref: int,
        soft_mask_xref: int | None,
    ) -> dict[str, Any]:
        pymupdf = cls._load_pymupdf()

        base_information = (
            source_document.extract_image(
                int(
                    xref
                )
            )
        )

        if not isinstance(
            base_information,
            dict,
        ):
            raise ValueError(
                "Source PDF returned invalid image metadata."
            )

        base_payload = (
            base_information.get(
                "image"
            )
        )

        if not base_payload:
            raise ValueError(
                "Source PDF xref contains no image bytes."
            )

        resolved_soft_mask_xref = (
            soft_mask_xref
        )

        if (
            resolved_soft_mask_xref
            is None
        ):
            resolved_soft_mask_xref = (
                cls._positive_integer_or_none(
                    base_information.get(
                        "smask"
                    )
                )
            )

        base_pixmap = pymupdf.Pixmap(
            base_payload
        )

        used_soft_mask = False

        if (
            resolved_soft_mask_xref
            is not None
        ):
            mask_information = (
                source_document.extract_image(
                    int(
                        resolved_soft_mask_xref
                    )
                )
            )

            mask_payload = (
                mask_information.get(
                    "image"
                )
                if isinstance(
                    mask_information,
                    dict,
                )
                else None
            )

            if not mask_payload:
                raise ValueError(
                    (
                        "Soft-mask xref contains "
                        "no image bytes."
                    )
                )

            mask_pixmap = pymupdf.Pixmap(
                mask_payload
            )

            if (
                mask_pixmap.width
                != base_pixmap.width
                or mask_pixmap.height
                != base_pixmap.height
            ):
                mask_pixmap = pymupdf.Pixmap(
                    mask_pixmap,
                    base_pixmap.width,
                    base_pixmap.height,
                )

            if (
                mask_pixmap.colorspace
                is not None
                and getattr(
                    mask_pixmap.colorspace,
                    "n",
                    1,
                )
                != 1
            ):
                mask_pixmap = pymupdf.Pixmap(
                    pymupdf.csGRAY,
                    mask_pixmap,
                )

            if base_pixmap.alpha:
                base_pixmap = pymupdf.Pixmap(
                    base_pixmap,
                    0,
                )

            base_pixmap = pymupdf.Pixmap(
                base_pixmap,
                mask_pixmap,
            )

            used_soft_mask = True

        return cls._pixmap_to_payload_result(
            pixmap=base_pixmap,
            pymupdf=pymupdf,
            used_soft_mask=(
                used_soft_mask
            ),
        )

    # ---------------------------------------------------------
    # Source-page region rendering
    # ---------------------------------------------------------

    @classmethod
    def _render_page_region(
        cls,
        *,
        source_page,
        bbox: Rectangle,
        dpi: int,
    ) -> dict[str, Any]:
        normalized_dpi = max(
            cls.MINIMUM_REGION_DPI,
            min(
                int(
                    dpi
                ),
                cls.MAXIMUM_REGION_DPI,
            ),
        )

        custom_renderer = getattr(
            source_page,
            "render_region",
            None,
        )

        if callable(
            custom_renderer
        ):
            result = custom_renderer(
                bbox=bbox,
                dpi=normalized_dpi,
            )

            if isinstance(
                result,
                dict,
            ):
                payload = result.get(
                    "payload"
                ) or result.get(
                    "image"
                )

            else:
                payload = result

            if not isinstance(
                payload,
                (
                    bytes,
                    bytearray,
                    memoryview,
                ),
            ):
                raise ValueError(
                    (
                        "Custom page-region renderer "
                        "returned no image bytes."
                    )
                )

            return cls._normalize_image_bytes(
                bytes(
                    payload
                )
            )

        pymupdf = cls._load_pymupdf()

        width_points = max(
            float(
                bbox.right
            )
            - float(
                bbox.left
            ),
            0.01,
        )

        height_points = max(
            float(
                bbox.bottom
            )
            - float(
                bbox.top
            ),
            0.01,
        )

        scale = (
            normalized_dpi
            / 72.0
        )

        estimated_width = (
            width_points
            * scale
        )

        estimated_height = (
            height_points
            * scale
        )

        if (
            estimated_width
            > cls.MAXIMUM_PIXEL_DIMENSION
        ):
            scale *= (
                cls.MAXIMUM_PIXEL_DIMENSION
                / estimated_width
            )

            estimated_width = (
                width_points
                * scale
            )

            estimated_height = (
                height_points
                * scale
            )

        if (
            estimated_height
            > cls.MAXIMUM_PIXEL_DIMENSION
        ):
            scale *= (
                cls.MAXIMUM_PIXEL_DIMENSION
                / estimated_height
            )

            estimated_width = (
                width_points
                * scale
            )

            estimated_height = (
                height_points
                * scale
            )

        estimated_pixel_count = (
            estimated_width
            * estimated_height
        )

        if (
            estimated_pixel_count
            > cls.MAXIMUM_PIXEL_COUNT
        ):
            scale *= math.sqrt(
                cls.MAXIMUM_PIXEL_COUNT
                / estimated_pixel_count
            )

        clip = pymupdf.Rect(
            float(
                bbox.left
            ),
            float(
                bbox.top
            ),
            float(
                bbox.right
            ),
            float(
                bbox.bottom
            ),
        )

        matrix = pymupdf.Matrix(
            scale,
            scale,
        )

        pixmap = source_page.get_pixmap(
            matrix=matrix,
            clip=clip,
            alpha=True,
        )

        return cls._pixmap_to_payload_result(
            pixmap=pixmap,
            pymupdf=pymupdf,
            used_soft_mask=False,
        )

    # ---------------------------------------------------------
    # Pixmap normalization
    # ---------------------------------------------------------

    @classmethod
    def _pixmap_to_payload_result(
        cls,
        *,
        pixmap,
        pymupdf,
        used_soft_mask: bool,
    ) -> dict[str, Any]:
        if (
            pixmap.width <= 0
            or pixmap.height <= 0
        ):
            raise ValueError(
                "Decoded image has invalid pixel dimensions."
            )

        colorspace = getattr(
            pixmap,
            "colorspace",
            None,
        )

        if (
            colorspace is not None
            and getattr(
                colorspace,
                "n",
                0,
            )
            > 3
        ):
            pixmap = pymupdf.Pixmap(
                pymupdf.csRGB,
                pixmap,
            )

        payload = pixmap.tobytes(
            "png"
        )

        if not payload:
            raise ValueError(
                "PNG normalization returned no bytes."
            )

        return {
            "payload": payload,
            "extension": "png",
            "mime_type": "image/png",
            "pixel_width": int(
                pixmap.width
            ),
            "pixel_height": int(
                pixmap.height
            ),
            "has_alpha": bool(
                pixmap.alpha
            ),
            "used_soft_mask": bool(
                used_soft_mask
            ),
            "checksum": hashlib.sha256(
                payload
            ).hexdigest(),
        }

    # ---------------------------------------------------------
    # Apply and reset
    # ---------------------------------------------------------

    @classmethod
    def _apply_payload_result(
        cls,
        *,
        image: EditableImage,
        payload_result: dict[str, Any],
        payload_status: EditableImagePayloadStatus,
        payload_confidence: float,
    ) -> None:
        payload = payload_result.get(
            "payload"
        )

        if not isinstance(
            payload,
            bytes,
        ) or not payload:
            raise ValueError(
                "Resolved image payload is empty."
            )

        image.payload = payload

        image.payload_status = (
            payload_status
        )

        image.extension = str(
            payload_result.get(
                "extension"
            )
            or "png"
        )

        image.payload_mime_type = str(
            payload_result.get(
                "mime_type"
            )
            or "image/png"
        )

        image.payload_checksum = str(
            payload_result.get(
                "checksum"
            )
            or hashlib.sha256(
                payload
            ).hexdigest()
        )

        image.pixel_width = int(
            payload_result.get(
                "pixel_width"
            )
            or image.pixel_width
            or 0
        ) or None

        image.pixel_height = int(
            payload_result.get(
                "pixel_height"
            )
            or image.pixel_height
            or 0
        ) or None

        image.has_alpha = bool(
            payload_result.get(
                "has_alpha",
                image.has_alpha,
            )
        )

        image.used_soft_mask = bool(
            payload_result.get(
                "used_soft_mask",
                False,
            )
        )

        image.payload_confidence = max(
            0.0,
            min(
                float(
                    payload_confidence
                ),
                1.0,
            ),
        )

        image.payload_error = None

    @classmethod
    def _reset_payload_state(
        cls,
        image: EditableImage,
    ) -> None:
        image.payload_status = (
            EditableImagePayloadStatus
            .UNRESOLVED
        )

        image.payload_mime_type = None

        image.payload_checksum = None

        image.payload_confidence = 0.0

        image.payload_error = None

        image.used_soft_mask = False

        image.reasons = [
            reason
            for reason in image.reasons
            if not reason.startswith(
                cls.MESSAGE_PREFIX
            )
        ]

        image.warnings = [
            warning
            for warning in image.warnings
            if not warning.startswith(
                cls.MESSAGE_PREFIX
            )
        ]

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _positive_integer_or_none(
        value,
    ) -> int | None:
        try:
            normalized = int(
                value
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

        return (
            normalized
            if normalized > 0
            else None
        )

    @staticmethod
    def _load_pymupdf():
        try:
            import pymupdf

            return pymupdf

        except ImportError:
            import fitz as pymupdf

            return pymupdf