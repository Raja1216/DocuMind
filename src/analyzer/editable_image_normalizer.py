from __future__ import annotations

import math
from typing import Any

from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImageExtractionMode,
    normalize_extension,
    normalize_payload,
    positive_integer_or_none,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableImageNormalizer:
    """
    Convert extraction-side image placements into generalized
    editable-image intermediate models.

    This analyzer does not decide whether an image should be
    inline, floating, behind text, or an overlay.
    """

    GEOMETRY_TOLERANCE = 0.01

    PAYLOAD_ATTRIBUTE_NAMES = (
        "payload",
        "image_bytes",
        "data",
        "stream",
        "bytes",
        "binary_data",
    )

    XREF_ATTRIBUTE_NAMES = (
        "xref",
        "image_xref",
        "object_xref",
        "resource_xref",
    )

    SOFT_MASK_ATTRIBUTE_NAMES = (
        "soft_mask_xref",
        "smask",
        "mask_xref",
        "softmask",
    )

    EXTENSION_ATTRIBUTE_NAMES = (
        "extension",
        "ext",
        "image_format",
        "format",
        "mime_type",
        "content_type",
    )

    PIXEL_WIDTH_ATTRIBUTE_NAMES = (
        "pixel_width",
        "image_width",
        "source_width",
        "width_px",
        "width",
    )

    PIXEL_HEIGHT_ATTRIBUTE_NAMES = (
        "pixel_height",
        "image_height",
        "source_height",
        "height_px",
        "height",
    )

    ROTATION_ATTRIBUTE_NAMES = (
        "rotation",
        "angle",
        "rotate",
    )

    OPACITY_ATTRIBUTE_NAMES = (
        "opacity",
        "image_opacity",
        "fill_opacity",
    )

    ALPHA_ATTRIBUTE_NAMES = (
        "has_alpha",
        "has_transparency",
        "transparent",
        "alpha_channel",
    )

    @classmethod
    def normalize_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.normalize_page(
                page
            )

    @classmethod
    def normalize_page(
        cls,
        page,
    ) -> list[EditableImage]:
        normalized_images: list[
            EditableImage
        ] = []

        source_images = list(
            getattr(
                page,
                "images",
                [],
            )
            or []
        )

        for image_index, source_image in enumerate(
            source_images
        ):
            normalized_images.append(
                cls.normalize_image(
                    page=page,
                    source_image=source_image,
                    image_index=image_index,
                )
            )

        # Reanalysis replaces stale image models.
        page.editable_images = (
            normalized_images
        )

        return normalized_images

    @classmethod
    def normalize_image(
        cls,
        *,
        page,
        source_image,
        image_index: int,
    ) -> EditableImage:
        page_number = cls._positive_integer(
            getattr(
                page,
                "number",
                1,
            ),
            fallback=1,
        )

        image_id = (
            f"image:"
            f"{page_number}:"
            f"{image_index + 1}"
        )

        source_bbox = (
            cls._rectangle_from_source(
                source_image
            )
        )

        page_bbox = (
            cls._rectangle_from_source(
                getattr(
                    page,
                    "bbox",
                    page,
                )
            )
        )

        geometry_is_valid = (
            source_bbox is not None
            and cls._rectangle_has_area(
                source_bbox
            )
        )

        clipped_bbox = source_bbox

        was_clipped = False

        completely_outside = False

        if (
            geometry_is_valid
            and page_bbox is not None
            and cls._rectangle_has_area(
                page_bbox
            )
        ):
            (
                clipped_bbox,
                was_clipped,
            ) = cls._intersect_rectangles(
                source_bbox,
                page_bbox,
            )

            if clipped_bbox is None:
                completely_outside = True
                geometry_is_valid = False

        if clipped_bbox is None:
            clipped_bbox = Rectangle(
                left=0.0,
                top=0.0,
                right=0.0,
                bottom=0.0,
            )

        payload = cls._resolve_payload(
            source_image
        )

        xref = cls._resolve_positive_integer(
            source_image,
            cls.XREF_ATTRIBUTE_NAMES,
        )

        soft_mask_xref = (
            cls._resolve_positive_integer(
                source_image,
                cls.SOFT_MASK_ATTRIBUTE_NAMES,
            )
        )

        pixel_width = (
            cls._resolve_positive_integer(
                source_image,
                cls.PIXEL_WIDTH_ATTRIBUTE_NAMES,
            )
        )

        pixel_height = (
            cls._resolve_positive_integer(
                source_image,
                cls.PIXEL_HEIGHT_ATTRIBUTE_NAMES,
            )
        )

        extension = cls._resolve_extension(
            source_image
        )

        rotation = cls._resolve_float(
            source_image,
            cls.ROTATION_ATTRIBUTE_NAMES,
            fallback=0.0,
        )

        opacity = cls._resolve_opacity(
            source_image
        )

        has_alpha = cls._resolve_boolean(
            source_image,
            cls.ALPHA_ATTRIBUTE_NAMES,
        )

        if (
            soft_mask_xref is not None
            and soft_mask_xref > 0
        ):
            has_alpha = True

        source_pdf_page = getattr(
            page,
            "source_pdf_page",
            None,
        )

        extraction_mode = (
            EditableImageExtractionMode
            .UNAVAILABLE
        )

        disposition = (
            EditableImageDisposition.SKIP
        )

        if geometry_is_valid:
            if payload is not None:
                extraction_mode = (
                    EditableImageExtractionMode
                    .DIRECT_BYTES
                )

                disposition = (
                    EditableImageDisposition
                    .NATIVE
                )

            elif xref is not None:
                extraction_mode = (
                    EditableImageExtractionMode
                    .PDF_XREF
                )

                disposition = (
                    EditableImageDisposition
                    .NATIVE
                )

            elif source_pdf_page is not None:
                extraction_mode = (
                    EditableImageExtractionMode
                    .PAGE_REGION
                )

                disposition = (
                    EditableImageDisposition
                    .REGION_FALLBACK
                )

        confidence = cls._calculate_confidence(
            geometry_is_valid=(
                geometry_is_valid
            ),
            extraction_mode=(
                extraction_mode
            ),
            pixel_width=pixel_width,
            pixel_height=pixel_height,
            extension=extension,
            xref=xref,
            source_image=source_image,
            bbox=clipped_bbox,
        )

        image = EditableImage(
            page_number=page_number,
            image_id=image_id,
            bbox=clipped_bbox,
            source_image=source_image,
            extraction_mode=(
                extraction_mode
            ),
            disposition=disposition,
            payload=payload,
            extension=extension,
            xref=xref,
            soft_mask_xref=(
                soft_mask_xref
            ),
            pixel_width=pixel_width,
            pixel_height=pixel_height,
            rotation=rotation,
            opacity=opacity,
            has_alpha=has_alpha,
            confidence=confidence,
        )

        if completely_outside:
            image.add_warning(
                (
                    "Image placement lies completely "
                    "outside the source page."
                )
            )

            image.add_reason(
                "Invalid image-page intersection."
            )

        elif not geometry_is_valid:
            image.add_warning(
                (
                    "Image placement has missing or "
                    "zero-area geometry."
                )
            )

            image.add_reason(
                "Invalid image geometry."
            )

        elif was_clipped:
            image.add_warning(
                (
                    "Image geometry was clipped to "
                    "the source-page boundaries."
                )
            )

        if (
            extraction_mode
            == EditableImageExtractionMode
            .DIRECT_BYTES
        ):
            image.add_reason(
                (
                    "Direct image bytes are available "
                    "for later native rendering."
                )
            )

        elif (
            extraction_mode
            == EditableImageExtractionMode
            .PDF_XREF
        ):
            image.add_reason(
                (
                    "Image pixels can be extracted "
                    "from the source PDF xref."
                )
            )

        elif (
            extraction_mode
            == EditableImageExtractionMode
            .PAGE_REGION
        ):
            image.add_reason(
                (
                    "Image will require source-page "
                    "region rendering."
                )
            )

        else:
            image.add_warning(
                (
                    "No direct bytes, PDF xref, or "
                    "source-page fallback is available."
                )
            )

            image.add_reason(
                "Image pixels are unavailable."
            )

        return image

    # ---------------------------------------------------------
    # Geometry
    # ---------------------------------------------------------

    @classmethod
    def _rectangle_from_source(
        cls,
        source,
    ) -> Rectangle | None:
        if source is None:
            return None

        geometry_source = getattr(
            source,
            "bbox",
            None,
        )

        if geometry_source is None:
            geometry_source = getattr(
                source,
                "rect",
                None,
            )

        if geometry_source is None:
            geometry_source = source

        left = cls._first_finite_number(
            geometry_source,
            (
                "left",
                "x0",
            ),
        )

        top = cls._first_finite_number(
            geometry_source,
            (
                "top",
                "y0",
            ),
        )

        right = cls._first_finite_number(
            geometry_source,
            (
                "right",
                "x1",
            ),
        )

        bottom = cls._first_finite_number(
            geometry_source,
            (
                "bottom",
                "y1",
            ),
        )

        if any(
            value is None
            for value in (
                left,
                top,
                right,
                bottom,
            )
        ):
            return None

        if right < left:
            left, right = (
                right,
                left,
            )

        if bottom < top:
            top, bottom = (
                bottom,
                top,
            )

        return Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )

    @classmethod
    def _rectangle_has_area(
        cls,
        rectangle: Rectangle,
    ) -> bool:
        return (
            float(
                rectangle.right
            )
            - float(
                rectangle.left
            )
            > cls.GEOMETRY_TOLERANCE
            and float(
                rectangle.bottom
            )
            - float(
                rectangle.top
            )
            > cls.GEOMETRY_TOLERANCE
        )

    @classmethod
    def _intersect_rectangles(
        cls,
        source: Rectangle,
        container: Rectangle,
    ) -> tuple[
        Rectangle | None,
        bool,
    ]:
        left = max(
            float(
                source.left
            ),
            float(
                container.left
            ),
        )

        top = max(
            float(
                source.top
            ),
            float(
                container.top
            ),
        )

        right = min(
            float(
                source.right
            ),
            float(
                container.right
            ),
        )

        bottom = min(
            float(
                source.bottom
            ),
            float(
                container.bottom
            ),
        )

        if (
            right - left
            <= cls.GEOMETRY_TOLERANCE
            or bottom - top
            <= cls.GEOMETRY_TOLERANCE
        ):
            return (
                None,
                False,
            )

        clipped = (
            abs(
                left
                - float(
                    source.left
                )
            )
            > cls.GEOMETRY_TOLERANCE
            or abs(
                top
                - float(
                    source.top
                )
            )
            > cls.GEOMETRY_TOLERANCE
            or abs(
                right
                - float(
                    source.right
                )
            )
            > cls.GEOMETRY_TOLERANCE
            or abs(
                bottom
                - float(
                    source.bottom
                )
            )
            > cls.GEOMETRY_TOLERANCE
        )

        return (
            Rectangle(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            ),
            clipped,
        )

    # ---------------------------------------------------------
    # Extraction metadata
    # ---------------------------------------------------------

    @classmethod
    def _resolve_payload(
        cls,
        source_image,
    ) -> bytes | None:
        for attribute_name in (
            cls.PAYLOAD_ATTRIBUTE_NAMES
        ):
            value = getattr(
                source_image,
                attribute_name,
                None,
            )

            if callable(
                value
            ):
                continue

            payload = normalize_payload(
                value
            )

            if payload is not None:
                return payload

        return None

    @classmethod
    def _resolve_extension(
        cls,
        source_image,
    ) -> str | None:
        for attribute_name in (
            cls.EXTENSION_ATTRIBUTE_NAMES
        ):
            value = getattr(
                source_image,
                attribute_name,
                None,
            )

            if value is None:
                continue

            normalized = normalize_extension(
                str(
                    value
                )
            )

            if normalized:
                return normalized

        return None

    @classmethod
    def _resolve_positive_integer(
        cls,
        source,
        attribute_names: tuple[str, ...],
    ) -> int | None:
        for attribute_name in (
            attribute_names
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            normalized = (
                positive_integer_or_none(
                    value
                )
            )

            if normalized is not None:
                return normalized

        return None

    @classmethod
    def _resolve_float(
        cls,
        source,
        attribute_names: tuple[str, ...],
        *,
        fallback: float,
    ) -> float:
        for attribute_name in (
            attribute_names
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            try:
                normalized = float(
                    value
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if math.isfinite(
                normalized
            ):
                return normalized

        return float(
            fallback
        )

    @classmethod
    def _resolve_opacity(
        cls,
        source_image,
    ) -> float:
        raw_value = cls._resolve_float(
            source_image,
            cls.OPACITY_ATTRIBUTE_NAMES,
            fallback=1.0,
        )

        if raw_value <= 1.0:
            return max(
                raw_value,
                0.0,
            )

        if raw_value <= 100.0:
            return max(
                0.0,
                min(
                    raw_value / 100.0,
                    1.0,
                ),
            )

        if raw_value <= 255.0:
            return max(
                0.0,
                min(
                    raw_value / 255.0,
                    1.0,
                ),
            )

        return 1.0

    @staticmethod
    def _resolve_boolean(
        source,
        attribute_names: tuple[str, ...],
    ) -> bool:
        for attribute_name in (
            attribute_names
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            if isinstance(
                value,
                bool,
            ):
                if value:
                    return True

            elif value is not None:
                normalized = str(
                    value
                ).strip().casefold()

                if normalized in {
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                }:
                    return True

        return False

    # ---------------------------------------------------------
    # Confidence
    # ---------------------------------------------------------

    @classmethod
    def _calculate_confidence(
        cls,
        *,
        geometry_is_valid: bool,
        extraction_mode: (
            EditableImageExtractionMode
        ),
        pixel_width: int | None,
        pixel_height: int | None,
        extension: str | None,
        xref: int | None,
        source_image: Any,
        bbox: Rectangle,
    ) -> float:
        confidence = 0.0

        if geometry_is_valid:
            confidence += 0.30

        if (
            extraction_mode
            != EditableImageExtractionMode
            .UNAVAILABLE
        ):
            confidence += 0.30

        if (
            pixel_width is not None
            and pixel_height is not None
        ):
            confidence += 0.15

        if extension:
            confidence += 0.10

        if (
            xref is not None
            or source_image is not None
        ):
            confidence += 0.10

        if (
            float(
                bbox.right
            )
            > float(
                bbox.left
            )
            and float(
                bbox.bottom
            )
            > float(
                bbox.top
            )
        ):
            confidence += 0.05

        return max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )

    # ---------------------------------------------------------
    # Primitive helpers
    # ---------------------------------------------------------

    @staticmethod
    def _first_finite_number(
        source,
        attribute_names: tuple[str, ...],
    ) -> float | None:
        for attribute_name in (
            attribute_names
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            try:
                normalized = float(
                    value
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if math.isfinite(
                normalized
            ):
                return normalized

        return None

    @staticmethod
    def _positive_integer(
        value,
        *,
        fallback: int,
    ) -> int:
        normalized = positive_integer_or_none(
            value
        )

        return (
            normalized
            if normalized is not None
            else fallback
        )