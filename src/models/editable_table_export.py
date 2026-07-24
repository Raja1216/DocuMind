from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EditableTableExportMode(
    str,
    Enum,
):
    """
    Final output representation used for one table.
    """

    NATIVE = "native"

    VISUAL_FALLBACK = "visual_fallback"

    SKIPPED = "skipped"

    FAILED = "failed"


@dataclass(slots=True)
class EditableTableExportResult:
    """
    Runtime export result for one table.

    Validation decides what should be attempted. This model records
    what actually happened while writing the DOCX package.
    """

    table_id: str

    page_number: int

    requested_mode: EditableTableExportMode

    final_mode: EditableTableExportMode = (
        EditableTableExportMode.FAILED
    )

    success: bool = False

    native_attempted: bool = False

    fallback_attempted: bool = False

    native_error: str | None = None

    fallback_error: str | None = None

    rendered_width: float = 0.0

    rendered_height: float = 0.0

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(
        self,
    ) -> None:
        self.table_id = str(
            self.table_id
            or ""
        ).strip()

        if not self.table_id:
            raise ValueError(
                "table export result table_id cannot be empty"
            )

        self.page_number = max(
            int(
                self.page_number
            ),
            1,
        )

        self.rendered_width = max(
            float(
                self.rendered_width
            ),
            0.0,
        )

        self.rendered_height = max(
            float(
                self.rendered_height
            ),
            0.0,
        )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
            or ""
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )
