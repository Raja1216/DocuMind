from __future__ import annotations

from dataclasses import dataclass, field

from src.models.page_profile import (
    ConversionMode,
)


@dataclass(slots=True)
class ConversionPolicy:
    """
    Describes how one PDF page should eventually be exported
    to DOCX.

    This model stores decisions only. It does not perform any
    DOCX rendering.
    """

    page_number: int

    mode: ConversionMode = (
        ConversionMode.HYBRID
    )

    # ---------------------------------------------------------
    # Editable semantic content
    # ---------------------------------------------------------

    export_text_as_paragraphs: bool = True

    export_lists_as_word_lists: bool = True

    export_tables_as_word_tables: bool = True

    export_forms_as_controls: bool = False

    # ---------------------------------------------------------
    # Visual content
    # ---------------------------------------------------------

    export_images_as_images: bool = True

    export_vectors_as_images: bool = False

    export_charts_as_images: bool = True

    # ---------------------------------------------------------
    # OCR
    # ---------------------------------------------------------

    run_ocr: bool = False

    include_ocr_text: bool = False

    # ---------------------------------------------------------
    # Fallback behaviour
    # ---------------------------------------------------------

    use_full_page_image: bool = False

    allow_region_image_fallback: bool = True

    # ---------------------------------------------------------
    # Word page behaviour
    # ---------------------------------------------------------

    preserve_original_page_size: bool = True

    preserve_page_break: bool = True

    # ---------------------------------------------------------
    # Decision metadata
    # ---------------------------------------------------------

    confidence: float = 0.0

    reason: str = ""

    warnings: list[str] = field(
        default_factory=list
    )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        """
        Add a policy warning without creating duplicates.
        """

        normalized_warning = (
            warning.strip()
        )

        if (
            normalized_warning
            and normalized_warning
            not in self.warnings
        ):
            self.warnings.append(
                normalized_warning
            )