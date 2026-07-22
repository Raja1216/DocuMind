from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EditableTableValidationSeverity(
    str,
    Enum,
):
    """
    Severity assigned to one table-validation issue.
    """

    INFO = "info"

    WARNING = "warning"

    ERROR = "error"


class EditableTableRenderDecision(
    str,
    Enum,
):
    """
    Final table-rendering decision after generalized validation.
    """

    NATIVE_SAFE = "native_safe"

    NATIVE_WITH_WARNINGS = "native_with_warnings"

    VISUAL_FALLBACK = "visual_fallback"

    SKIP = "skip"


@dataclass(slots=True)
class EditableTableValidationIssue:
    """
    One generalized validation observation.

    ``code`` is stable and suitable for diagnostics and regression
    assertions. It must not contain sample-specific text.
    """

    code: str

    message: str

    severity: EditableTableValidationSeverity

    row_index: int | None = None

    column_index: int | None = None

    def __post_init__(
        self,
    ) -> None:
        self.code = str(
            self.code
            or ""
        ).strip()

        self.message = str(
            self.message
            or ""
        ).strip()

        if not self.code:
            raise ValueError(
                "validation issue code cannot be empty"
            )

        if not self.message:
            raise ValueError(
                "validation issue message cannot be empty"
            )

        self.row_index = (
            normalize_optional_integer(
                self.row_index
            )
        )

        self.column_index = (
            normalize_optional_integer(
                self.column_index
            )
        )


@dataclass(slots=True)
class EditableTableValidationReport:
    """
    Validation result for one editable-table candidate.
    """

    table_id: str

    page_number: int

    decision: EditableTableRenderDecision = (
        EditableTableRenderDecision
        .VISUAL_FALLBACK
    )

    native_confidence: float = 0.0

    issues: list[
        EditableTableValidationIssue
    ] = field(
        default_factory=list
    )

    metrics: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
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
                "validation report table_id cannot be empty"
            )

        self.page_number = max(
            int(
                self.page_number
            ),
            1,
        )

        self.native_confidence = (
            clamp_confidence(
                self.native_confidence
            )
        )

    @property
    def errors(
        self,
    ) -> list[
        EditableTableValidationIssue
    ]:
        return [
            issue
            for issue in self.issues
            if (
                issue.severity
                == EditableTableValidationSeverity
                .ERROR
            )
        ]

    @property
    def warnings(
        self,
    ) -> list[
        EditableTableValidationIssue
    ]:
        return [
            issue
            for issue in self.issues
            if (
                issue.severity
                == EditableTableValidationSeverity
                .WARNING
            )
        ]

    @property
    def infos(
        self,
    ) -> list[
        EditableTableValidationIssue
    ]:
        return [
            issue
            for issue in self.issues
            if (
                issue.severity
                == EditableTableValidationSeverity
                .INFO
            )
        ]

    @property
    def is_native(
        self,
    ) -> bool:
        return self.decision in {
            EditableTableRenderDecision
            .NATIVE_SAFE,
            EditableTableRenderDecision
            .NATIVE_WITH_WARNINGS,
        }

    @property
    def requires_visual_fallback(
        self,
    ) -> bool:
        return (
            self.decision
            == EditableTableRenderDecision
            .VISUAL_FALLBACK
        )

    def add_issue(
        self,
        *,
        code: str,
        message: str,
        severity: EditableTableValidationSeverity,
        row_index: int | None = None,
        column_index: int | None = None,
    ) -> None:
        issue = EditableTableValidationIssue(
            code=code,
            message=message,
            severity=severity,
            row_index=row_index,
            column_index=column_index,
        )

        signature = (
            issue.code,
            issue.message,
            issue.severity,
            issue.row_index,
            issue.column_index,
        )

        existing_signatures = {
            (
                existing.code,
                existing.message,
                existing.severity,
                existing.row_index,
                existing.column_index,
            )
            for existing in self.issues
        }

        if signature not in existing_signatures:
            self.issues.append(
                issue
            )

    def set_metric(
        self,
        name: str,
        value: Any,
    ) -> None:
        normalized_name = str(
            name
            or ""
        ).strip()

        if not normalized_name:
            raise ValueError(
                "metric name cannot be empty"
            )

        self.metrics[
            normalized_name
        ] = value

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        self.native_confidence = (
            clamp_confidence(
                confidence
            )
        )


def clamp_confidence(
    confidence: float,
) -> float:
    return max(
        0.0,
        min(
            float(
                confidence
            ),
            1.0,
        ),
    )


def normalize_optional_integer(
    value,
) -> int | None:
    if value is None:
        return None

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None
