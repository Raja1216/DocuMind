from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableImageDisposition(
    str,
    Enum,
):
    """
    Final strategy for one normalized image placement.
    """

    NATIVE = "native"

    REGION_FALLBACK = "region_fallback"

    SKIP = "skip"


class EditableImageExtractionMode(
    str,
    Enum,
):
    """
    How image pixels can be obtained later.
    """

    DIRECT_BYTES = "direct_bytes"

    PDF_XREF = "pdf_xref"

    PAGE_REGION = "page_region"

    UNAVAILABLE = "unavailable"


class EditableImageRole(
    str,
    Enum,
):
    """
    Semantic role of an image.

    Role classification happens in a later step.
    """

    CONTENT = "content"

    LOGO = "logo"

    DECORATION = "decoration"

    BACKGROUND = "background"

    WATERMARK = "watermark"

    UNKNOWN = "unknown"


class EditableImagePlacement(
    str,
    Enum,
):
    """
    Intended Word placement.

    Placement planning happens in Step 64G.1.2.
    """

    INLINE = "inline"

    FLOATING = "floating"

    BACKGROUND = "background"

    OVERLAY = "overlay"

    UNRESOLVED = "unresolved"

class EditableImageAnchorPosition(
    str,
    Enum,
):
    """
    Image position relative to its anchor paragraph.
    """

    BEFORE = "before"

    AFTER = "after"

    NONE = "none"
    
class EditableImageHorizontalAlignment(
    str,
    Enum,
):
    """
    Approximate horizontal placement on the source page.
    """

    LEFT = "left"

    CENTER = "center"

    RIGHT = "right"

    ABSOLUTE = "absolute"    

class EditableImagePayloadStatus(
    str,
    Enum,
):
    """
    Runtime state of normalized image payload extraction.
    """

    UNRESOLVED = "unresolved"

    READY = "ready"

    REGION_RENDERED = "region_rendered"

    FAILED = "failed"

    SKIPPED = "skipped"

@dataclass(slots=True)
class EditableImage:
    """
    One normalized image placement on one PDF page.

    The same embedded image xref may produce multiple instances
    when it is placed several times.
    """

    page_number: int

    image_id: str

    bbox: Rectangle

    source_image: Any | None = field(
        default=None,
        repr=False,
    )

    extraction_mode: EditableImageExtractionMode = (
        EditableImageExtractionMode.UNAVAILABLE
    )

    disposition: EditableImageDisposition = (
        EditableImageDisposition.NATIVE
    )

    placement: EditableImagePlacement = (
        EditableImagePlacement.UNRESOLVED
    )

    role: EditableImageRole = (
        EditableImageRole.UNKNOWN
    )

    anchor_paragraph_region_number: (
        int | None
    ) = None

    anchor_position: (
        EditableImageAnchorPosition
    ) = EditableImageAnchorPosition.NONE

    horizontal_alignment: (
        EditableImageHorizontalAlignment
    ) = EditableImageHorizontalAlignment.ABSOLUTE

    placement_confidence: float = 0.0

    page_area_ratio: float = 0.0

    text_overlap_ratio: float = 0.0

    table_overlap_ratio: float = 0.0

    repeat_count: int = 1


    payload: bytes | None = field(
        default=None,
        repr=False,
    )

    payload_status: EditableImagePayloadStatus = (
        EditableImagePayloadStatus.UNRESOLVED
    )

    payload_mime_type: str | None = None

    payload_checksum: str | None = None

    payload_confidence: float = 0.0

    payload_error: str | None = None

    used_soft_mask: bool = False

    extension: str | None = None

    xref: int | None = None

    soft_mask_xref: int | None = None

    pixel_width: int | None = None

    pixel_height: int | None = None

    rotation: float = 0.0

    opacity: float = 1.0

    has_alpha: bool = False

    confidence: float = 0.0

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(
        self,
    ) -> None:
        if self.page_number < 1:
            raise ValueError(
                "page_number must be one or greater"
            )

        normalized_id = str(
            self.image_id
        ).strip()

        if not normalized_id:
            raise ValueError(
                "image_id cannot be empty"
            )

        self.image_id = normalized_id

        self.payload = normalize_payload(
            self.payload
        )

        self.extension = normalize_extension(
            self.extension
        )

        self.xref = positive_integer_or_none(
            self.xref
        )

        self.soft_mask_xref = (
            positive_integer_or_none(
                self.soft_mask_xref
            )
        )

        self.pixel_width = (
            positive_integer_or_none(
                self.pixel_width
            )
        )

        self.pixel_height = (
            positive_integer_or_none(
                self.pixel_height
            )
        )

        self.rotation = normalize_rotation(
            self.rotation
        )

        self.opacity = clamp_unit_value(
            self.opacity,
            fallback=1.0,
        )

        self.confidence = clamp_unit_value(
            self.confidence,
            fallback=0.0,
        )

        self.placement_confidence = (
            clamp_unit_value(
                self.placement_confidence,
                fallback=0.0,
            )
        )
        
        self.payload_confidence = (
            clamp_unit_value(
                self.payload_confidence,
                fallback=0.0,
            )
        )

        normalized_mime_type = str(
            self.payload_mime_type
            or ""
        ).strip().lower()

        self.payload_mime_type = (
            normalized_mime_type
            or None
        )

        normalized_checksum = str(
            self.payload_checksum
            or ""
        ).strip().lower()

        self.payload_checksum = (
            normalized_checksum
            or None
        )

        normalized_error = str(
            self.payload_error
            or ""
        ).strip()

        self.payload_error = (
            normalized_error
            or None
        )

        self.used_soft_mask = bool(
            self.used_soft_mask
        )

        self.page_area_ratio = clamp_unit_value(
            self.page_area_ratio,
            fallback=0.0,
        )

        self.text_overlap_ratio = (
            clamp_unit_value(
                self.text_overlap_ratio,
                fallback=0.0,
            )
        )

        self.table_overlap_ratio = (
            clamp_unit_value(
                self.table_overlap_ratio,
                fallback=0.0,
            )
        )

        try:
            normalized_repeat_count = int(
                self.repeat_count
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            normalized_repeat_count = 1

        self.repeat_count = max(
            normalized_repeat_count,
            1,
        )

        if (
            self.anchor_paragraph_region_number
            is not None
        ):
            try:
                self.anchor_paragraph_region_number = (
                    int(
                        self
                        .anchor_paragraph_region_number
                    )
                )
            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                self.anchor_paragraph_region_number = (
                    None
                )

        self.has_alpha = bool(
            self.has_alpha
        )

    @property
    def width(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.right
            )
            - float(
                self.bbox.left
            ),
            0.0,
        )

    @property
    def height(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.bottom
            )
            - float(
                self.bbox.top
            ),
            0.0,
        )

    @property
    def area(
        self,
    ) -> float:
        return (
            self.width
            * self.height
        )

    @property
    def aspect_ratio(
        self,
    ) -> float | None:
        if self.height <= 0.0:
            return None

        return (
            self.width
            / self.height
        )

    @property
    def pixel_aspect_ratio(
        self,
    ) -> float | None:
        if (
            self.pixel_width is None
            or self.pixel_height is None
            or self.pixel_height <= 0
        ):
            return None

        return (
            self.pixel_width
            / self.pixel_height
        )

    @property
    def has_valid_geometry(
        self,
    ) -> bool:
        return (
            self.width > 0.0
            and self.height > 0.0
        )

    @property
    def can_extract(
        self,
    ) -> bool:
        return (
            self.extraction_mode
            != EditableImageExtractionMode
            .UNAVAILABLE
        )

    @property
    def has_resolved_payload(
        self,
    ) -> bool:
        return (
            self.payload is not None
            and len(
                self.payload
            ) > 0
            and self.payload_status
            in {
                EditableImagePayloadStatus.READY,
                EditableImagePayloadStatus
                .REGION_RENDERED,
            }
        )

    def add_reason(
        self,
        reason: str,
    ) -> None:
        normalized = str(
            reason
        ).strip()

        if (
            normalized
            and normalized
            not in self.reasons
        ):
            self.reasons.append(
                normalized
            )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )


def normalize_payload(
    value,
) -> bytes | None:
    if value is None:
        return None

    if isinstance(
        value,
        bytes,
    ):
        return value or None

    if isinstance(
        value,
        bytearray,
    ):
        normalized = bytes(
            value
        )

        return normalized or None

    if isinstance(
        value,
        memoryview,
    ):
        normalized = value.tobytes()

        return normalized or None

    return None


def normalize_extension(
    value: str | None,
) -> str | None:
    normalized = str(
        value
        or ""
    ).strip().lower()

    if normalized.startswith(
        "image/"
    ):
        normalized = normalized.split(
            "/",
            1,
        )[1]

    normalized = normalized.lstrip(
        "."
    )

    aliases = {
        "jpg": "jpeg",
        "jpe": "jpeg",
        "tif": "tiff",
        "x-png": "png",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return normalized or None


def positive_integer_or_none(
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


def normalize_rotation(
    value,
) -> float:
    try:
        normalized = float(
            value
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return 0.0

    normalized %= 360.0

    if abs(
        normalized - 360.0
    ) <= 0.001:
        return 0.0

    return normalized


def clamp_unit_value(
    value,
    *,
    fallback: float,
) -> float:
    try:
        normalized = float(
            value
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        normalized = float(
            fallback
        )

    return max(
        0.0,
        min(
            normalized,
            1.0,
        ),
    )