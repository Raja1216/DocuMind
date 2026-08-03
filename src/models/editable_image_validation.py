from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EditableImageValidationSeverity(
    str,
    Enum,
):
    INFO = "info"

    WARNING = "warning"

    ERROR = "error"


class EditableImageRenderDecision(
    str,
    Enum,
):
    """
    Final generalized rendering decision for one normalized
    image placement.
    """

    NATIVE_INLINE_SAFE = (
        "native_inline_safe"
    )

    NATIVE_FLOATING_SAFE = (
        "native_floating_safe"
    )

    DEFER = "defer"

    SKIP = "skip"


@dataclass(slots=True)
class EditableImageValidationIssue:
    code: str

    message: str

    severity: (
        EditableImageValidationSeverity
    )

    def __post_init__(
        self,
    ) -> None:
        self.code = str(
            self.code
        ).strip().upper()

        self.message = str(
            self.message
        ).strip()

        if not self.code:
            raise ValueError(
                "Image validation issue code cannot be empty."
            )

        if not self.message:
            raise ValueError(
                "Image validation issue message cannot be empty."
            )


@dataclass(slots=True)
class EditableImageValidationReport:
    image_id: str

    page_number: int

    decision: EditableImageRenderDecision = (
        EditableImageRenderDecision.DEFER
    )

    native_confidence: float = 0.0

    issues: list[
        EditableImageValidationIssue
    ] = field(
        default_factory=list
    )

    def __post_init__(
        self,
    ) -> None:
        self.image_id = str(
            self.image_id
        ).strip()

        if not self.image_id:
            raise ValueError(
                "Image validation report requires image_id."
            )

        if int(
            self.page_number
        ) < 1:
            raise ValueError(
                "Image validation page number must be positive."
            )

        self.page_number = int(
            self.page_number
        )

        self.native_confidence = max(
            0.0,
            min(
                float(
                    self.native_confidence
                ),
                1.0,
            ),
        )

    @property
    def has_errors(
        self,
    ) -> bool:
        return any(
            issue.severity
            == EditableImageValidationSeverity
            .ERROR
            for issue in self.issues
        )

    @property
    def has_warnings(
        self,
    ) -> bool:
        return any(
            issue.severity
            == EditableImageValidationSeverity
            .WARNING
            for issue in self.issues
        )

    @property
    def can_render_inline(
        self,
    ) -> bool:
        return (
            self.decision
            == EditableImageRenderDecision
            .NATIVE_INLINE_SAFE
        )

    @property
    def can_render_floating(
        self,
    ) -> bool:
        return (
            self.decision
            == EditableImageRenderDecision
            .NATIVE_FLOATING_SAFE
        )

    @property
    def warning_messages(
        self,
    ) -> list[str]:
        return [
            issue.message
            for issue in self.issues
            if issue.severity
            in {
                EditableImageValidationSeverity
                .WARNING,
                EditableImageValidationSeverity
                .ERROR,
            }
        ]

    def add_issue(
        self,
        *,
        code: str,
        message: str,
        severity: (
            EditableImageValidationSeverity
        ),
    ) -> None:
        issue = EditableImageValidationIssue(
            code=code,
            message=message,
            severity=severity,
        )

        if not any(
            existing.code == issue.code
            and existing.message
            == issue.message
            and existing.severity
            == issue.severity
            for existing in self.issues
        ):
            self.issues.append(
                issue
            )