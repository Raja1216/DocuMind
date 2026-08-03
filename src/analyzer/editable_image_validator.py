from __future__ import annotations

import math

from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImagePayloadStatus,
    EditableImagePlacement,
)
from src.models.editable_image_validation import (
    EditableImageRenderDecision,
    EditableImageValidationReport,
    EditableImageValidationSeverity,
)


class EditableImageValidator:
    """
    Validate whether a normalized image can safely use one of
    the currently connected native Word renderers.

    This validator does not render images and contains no
    sample-, filename-, page- or coordinate-specific rules.
    """

    PNG_SIGNATURE = (
        b"\x89PNG\r\n\x1a\n"
    )

    GEOMETRY_TOLERANCE = 0.01

    ROTATION_TOLERANCE = 0.01

    MAXIMUM_NATIVE_PIXEL_COUNT = (
        40_000_000
    )

    MAXIMUM_NATIVE_PIXEL_DIMENSION = (
        12_000
    )

    MINIMUM_PAYLOAD_CONFIDENCE = 0.60

    MINIMUM_PLACEMENT_CONFIDENCE = 0.50

    MINIMUM_NATIVE_CONFIDENCE = 0.65

    ASPECT_RATIO_WARNING_DIFFERENCE = (
        0.35
    )

    @classmethod
    def validate_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.validate_page(
                page
            )

    @classmethod
    def validate_page(
        cls,
        page,
    ) -> dict[
        str,
        EditableImageValidationReport,
    ]:
        reports: dict[
            str,
            EditableImageValidationReport,
        ] = {}

        images = list(
            getattr(
                page,
                "editable_images",
                [],
            )
            or []
        )

        for image in images:
            report = cls.validate_image(
                page=page,
                image=image,
            )

            reports[
                image.image_id
            ] = report

        # Reanalysis replaces stale reports.
        page.editable_image_validation_reports = (
            reports
        )

        return reports

    @classmethod
    def validate_image(
        cls,
        *,
        page,
        image: EditableImage,
    ) -> EditableImageValidationReport:
        report = EditableImageValidationReport(
            image_id=image.image_id,
            page_number=image.page_number,
        )

        if (
            image.disposition
            == EditableImageDisposition.SKIP
        ):
            report.decision = (
                EditableImageRenderDecision.SKIP
            )

            report.add_issue(
                code="IMAGE_DISPOSITION_SKIP",
                message=(
                    "The normalized image disposition "
                    "is SKIP."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .INFO
                ),
            )

            return report

        geometry_score = (
            cls._validate_geometry(
                page=page,
                image=image,
                report=report,
            )
        )

        if geometry_score <= 0.0:
            report.decision = (
                EditableImageRenderDecision.SKIP
            )

            return report

        payload_score = (
            cls._validate_payload(
                image=image,
                report=report,
            )
        )

        metadata_score = (
            cls._validate_pixel_metadata(
                image=image,
                report=report,
            )
        )

        transform_score = (
            cls._validate_rotation(
                image=image,
                report=report,
            )
        )

        placement_score = (
            cls._validate_placement(
                page=page,
                image=image,
                report=report,
            )
        )

        confidence_score = (
            cls._calculate_native_confidence(
                image=image,
                geometry_score=geometry_score,
                payload_score=payload_score,
                metadata_score=metadata_score,
                transform_score=transform_score,
                placement_score=placement_score,
            )
        )

        report.native_confidence = (
            confidence_score
        )

        if report.has_errors:
            report.decision = (
                EditableImageRenderDecision.DEFER
            )

            return report

        if (
            confidence_score
            < cls.MINIMUM_NATIVE_CONFIDENCE
        ):
            report.add_issue(
                code="LOW_NATIVE_CONFIDENCE",
                message=(
                    "The combined native image "
                    "confidence is below the safe "
                    "rendering threshold."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

            report.decision = (
                EditableImageRenderDecision.DEFER
            )

            return report

        if (
            image.placement
            == EditableImagePlacement.INLINE
        ):
            report.decision = (
                EditableImageRenderDecision
                .NATIVE_INLINE_SAFE
            )

            return report

        if (
            image.placement
            == EditableImagePlacement.FLOATING
        ):
            report.decision = (
                EditableImageRenderDecision
                .NATIVE_FLOATING_SAFE
            )

            return report

        report.decision = (
            EditableImageRenderDecision.DEFER
        )

        return report

    # ---------------------------------------------------------
    # Geometry
    # ---------------------------------------------------------

    @classmethod
    def _validate_geometry(
        cls,
        *,
        page,
        image: EditableImage,
        report: EditableImageValidationReport,
    ) -> float:
        if not image.has_valid_geometry:
            report.add_issue(
                code="INVALID_IMAGE_GEOMETRY",
                message=(
                    "The image has zero-area or "
                    "otherwise invalid geometry."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        page_bbox = getattr(
            page,
            "bbox",
            None,
        )

        if page_bbox is None:
            report.add_issue(
                code="MISSING_PAGE_GEOMETRY",
                message=(
                    "The source page geometry is "
                    "not available."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        try:
            page_left = float(
                page_bbox.left
            )

            page_top = float(
                page_bbox.top
            )

            page_right = float(
                page_bbox.right
            )

            page_bottom = float(
                page_bbox.bottom
            )

            image_left = float(
                image.bbox.left
            )

            image_top = float(
                image.bbox.top
            )

            image_right = float(
                image.bbox.right
            )

            image_bottom = float(
                image.bbox.bottom
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            report.add_issue(
                code="UNREADABLE_IMAGE_GEOMETRY",
                message=(
                    "Image or page coordinates could "
                    "not be interpreted."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        coordinates = (
            page_left,
            page_top,
            page_right,
            page_bottom,
            image_left,
            image_top,
            image_right,
            image_bottom,
        )

        if not all(
            math.isfinite(
                coordinate
            )
            for coordinate in coordinates
        ):
            report.add_issue(
                code="NONFINITE_IMAGE_GEOMETRY",
                message=(
                    "Image or page coordinates contain "
                    "a non-finite value."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        intersection_width = max(
            min(
                image_right,
                page_right,
            )
            - max(
                image_left,
                page_left,
            ),
            0.0,
        )

        intersection_height = max(
            min(
                image_bottom,
                page_bottom,
            )
            - max(
                image_top,
                page_top,
            ),
            0.0,
        )

        if (
            intersection_width
            <= cls.GEOMETRY_TOLERANCE
            or intersection_height
            <= cls.GEOMETRY_TOLERANCE
        ):
            report.add_issue(
                code="IMAGE_OUTSIDE_PAGE",
                message=(
                    "The image placement does not "
                    "intersect the source page."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        is_clipped = (
            image_left
            < page_left
            - cls.GEOMETRY_TOLERANCE
            or image_top
            < page_top
            - cls.GEOMETRY_TOLERANCE
            or image_right
            > page_right
            + cls.GEOMETRY_TOLERANCE
            or image_bottom
            > page_bottom
            + cls.GEOMETRY_TOLERANCE
        )

        if is_clipped:
            report.add_issue(
                code="IMAGE_CLIPPED_TO_PAGE",
                message=(
                    "The image placement extends "
                    "outside the source page."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

            return 0.85

        return 1.0

    # ---------------------------------------------------------
    # Payload
    # ---------------------------------------------------------

    @classmethod
    def _validate_payload(
        cls,
        *,
        image: EditableImage,
        report: EditableImageValidationReport,
    ) -> float:
        if not image.has_resolved_payload:
            report.add_issue(
                code="MISSING_IMAGE_PAYLOAD",
                message=(
                    "The image does not have a "
                    "successfully resolved payload."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        if (
            image.payload_status
            not in {
                EditableImagePayloadStatus.READY,
                EditableImagePayloadStatus
                .REGION_RENDERED,
            }
        ):
            report.add_issue(
                code="UNSUPPORTED_PAYLOAD_STATUS",
                message=(
                    "The image payload status is not "
                    "supported by a native renderer."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        payload = image.payload

        if not isinstance(
            payload,
            bytes,
        ) or not payload:
            report.add_issue(
                code="INVALID_IMAGE_PAYLOAD",
                message=(
                    "The resolved image payload is "
                    "empty or not a byte sequence."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        if not payload.startswith(
            cls.PNG_SIGNATURE
        ):
            report.add_issue(
                code="UNNORMALIZED_IMAGE_PAYLOAD",
                message=(
                    "The resolved payload is not a "
                    "normalized PNG image."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        if (
            image.payload_confidence
            < cls.MINIMUM_PAYLOAD_CONFIDENCE
        ):
            report.add_issue(
                code="LOW_PAYLOAD_CONFIDENCE",
                message=(
                    "The image payload confidence is "
                    "below the safe native threshold."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return max(
                float(
                    image.payload_confidence
                ),
                0.0,
            )

        if (
            image.extension
            and str(
                image.extension
            ).casefold()
            != "png"
        ):
            report.add_issue(
                code="PAYLOAD_EXTENSION_MISMATCH",
                message=(
                    "The payload is normalized as PNG "
                    "but the stored extension differs."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

        if (
            image.payload_mime_type
            and str(
                image.payload_mime_type
            ).casefold()
            != "image/png"
        ):
            report.add_issue(
                code="PAYLOAD_MIME_MISMATCH",
                message=(
                    "The payload is normalized as PNG "
                    "but the stored MIME type differs."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

        return max(
            0.0,
            min(
                float(
                    image.payload_confidence
                ),
                1.0,
            ),
        )

    # ---------------------------------------------------------
    # Pixel metadata
    # ---------------------------------------------------------

    @classmethod
    def _validate_pixel_metadata(
        cls,
        *,
        image: EditableImage,
        report: EditableImageValidationReport,
    ) -> float:
        pixel_width = image.pixel_width

        pixel_height = image.pixel_height

        if (
            pixel_width is None
            or pixel_height is None
        ):
            report.add_issue(
                code="MISSING_PIXEL_DIMENSIONS",
                message=(
                    "The normalized image pixel "
                    "dimensions are unavailable."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

            return 0.65

        if (
            pixel_width <= 0
            or pixel_height <= 0
        ):
            report.add_issue(
                code="INVALID_PIXEL_DIMENSIONS",
                message=(
                    "The normalized image has invalid "
                    "pixel dimensions."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        if (
            pixel_width
            > cls.MAXIMUM_NATIVE_PIXEL_DIMENSION
            or pixel_height
            > cls.MAXIMUM_NATIVE_PIXEL_DIMENSION
            or (
                pixel_width
                * pixel_height
            )
            > cls.MAXIMUM_NATIVE_PIXEL_COUNT
        ):
            report.add_issue(
                code="IMAGE_PIXEL_LIMIT_EXCEEDED",
                message=(
                    "The image exceeds the safe "
                    "native pixel limit."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        source_ratio = (
            image.aspect_ratio
        )

        pixel_ratio = (
            image.pixel_aspect_ratio
        )

        if (
            source_ratio is not None
            and pixel_ratio is not None
            and source_ratio > 0.0
            and pixel_ratio > 0.0
        ):
            ratio_difference = (
                abs(
                    source_ratio
                    - pixel_ratio
                )
                / max(
                    source_ratio,
                    pixel_ratio,
                )
            )

            if (
                ratio_difference
                > cls
                .ASPECT_RATIO_WARNING_DIFFERENCE
            ):
                report.add_issue(
                    code="IMAGE_ASPECT_RATIO_DIFFERENCE",
                    message=(
                        "The PDF placement aspect "
                        "ratio differs significantly "
                        "from the pixel aspect ratio."
                    ),
                    severity=(
                        EditableImageValidationSeverity
                        .WARNING
                    ),
                )

                return 0.80

        return 1.0

    # ---------------------------------------------------------
    # Rotation and placement
    # ---------------------------------------------------------

    @classmethod
    def _validate_rotation(
        cls,
        *,
        image: EditableImage,
        report: EditableImageValidationReport,
    ) -> float:
        try:
            rotation = (
                float(
                    image.rotation
                )
                % 360.0
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            rotation = 0.0

        rotation_distance = min(
            abs(
                rotation
            ),
            abs(
                360.0 - rotation
            ),
        )

        if (
            rotation_distance
            > cls.ROTATION_TOLERANCE
        ):
            report.add_issue(
                code="UNSUPPORTED_IMAGE_ROTATION",
                message=(
                    "The current native image "
                    "renderers do not support "
                    "non-zero rotation."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

            return 0.0

        return 1.0

    @classmethod
    def _validate_placement(
        cls,
        *,
        page,
        image: EditableImage,
        report: EditableImageValidationReport,
    ) -> float:
        if (
            image.placement
            == EditableImagePlacement.INLINE
        ):
            placement_score = float(
                image.placement_confidence
            )

            if (
                image
                .anchor_paragraph_region_number
                is None
            ):
                report.add_issue(
                    code="INLINE_IMAGE_WITHOUT_ANCHOR",
                    message=(
                        "The inline image does not "
                        "have a paragraph-region anchor."
                    ),
                    severity=(
                        EditableImageValidationSeverity
                        .WARNING
                    ),
                )

                placement_score *= 0.90

        elif (
            image.placement
            == EditableImagePlacement.FLOATING
        ):
            if getattr(
                page,
                "bbox",
                None,
            ) is None:
                report.add_issue(
                    code="FLOATING_IMAGE_WITHOUT_PAGE",
                    message=(
                        "Floating image placement "
                        "requires source-page geometry."
                    ),
                    severity=(
                        EditableImageValidationSeverity
                        .ERROR
                    ),
                )

                return 0.0

            placement_score = float(
                image.placement_confidence
            )

        elif (
            image.placement
            == EditableImagePlacement.BACKGROUND
        ):
            report.add_issue(
                code="BACKGROUND_RENDERER_DEFERRED",
                message=(
                    "Background image rendering is "
                    "not connected yet."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .INFO
                ),
            )

            return 0.0

        elif (
            image.placement
            == EditableImagePlacement.OVERLAY
        ):
            report.add_issue(
                code="OVERLAY_RENDERER_DEFERRED",
                message=(
                    "Overlay image rendering is not "
                    "connected yet."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .INFO
                ),
            )

            return 0.0

        else:
            report.add_issue(
                code="UNRESOLVED_IMAGE_PLACEMENT",
                message=(
                    "The image placement has not "
                    "been resolved."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .WARNING
                ),
            )

            return 0.0

        if (
            placement_score
            < cls.MINIMUM_PLACEMENT_CONFIDENCE
        ):
            report.add_issue(
                code="LOW_PLACEMENT_CONFIDENCE",
                message=(
                    "The image placement confidence "
                    "is below the safe native threshold."
                ),
                severity=(
                    EditableImageValidationSeverity
                    .ERROR
                ),
            )

        return max(
            0.0,
            min(
                placement_score,
                1.0,
            ),
        )

    # ---------------------------------------------------------
    # Combined confidence
    # ---------------------------------------------------------

    @staticmethod
    def _calculate_native_confidence(
        *,
        image: EditableImage,
        geometry_score: float,
        payload_score: float,
        metadata_score: float,
        transform_score: float,
        placement_score: float,
    ) -> float:
        source_score = max(
            0.0,
            min(
                float(
                    image.confidence
                ),
                1.0,
            ),
        )

        confidence = (
            0.20 * geometry_score
            + 0.25 * payload_score
            + 0.15 * metadata_score
            + 0.10 * transform_score
            + 0.20 * placement_score
            + 0.10 * source_score
        )

        return max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )