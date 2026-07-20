from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlignmentValidationSeverity(str, Enum):
    """
    Severity of one validation issue.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AlignmentValidationCode(str, Enum):
    """
    Stable issue codes produced by the validation analyzer.
    """

    MISSING_RESULT = "missing_result"
    EXTRA_RESULT = "extra_result"
    DUPLICATE_RESULT = "duplicate_result"

    UNKNOWN_ALIGNMENT = "unknown_alignment"
    LOW_CONFIDENCE = "low_confidence"

    REFERENCE_MISMATCH = "reference_mismatch"
    PARAGRAPH_OUTSIDE_REFERENCE = (
        "paragraph_outside_reference"
    )

    CENTER_GEOMETRY_CONFLICT = (
        "center_geometry_conflict"
    )

    RIGHT_GEOMETRY_CONFLICT = (
        "right_geometry_conflict"
    )

    LEFT_GEOMETRY_CONFLICT = (
        "left_geometry_conflict"
    )

    JUSTIFY_GEOMETRY_CONFLICT = (
        "justify_geometry_conflict"
    )


@dataclass(slots=True)
class AlignmentValidationIssue:
    """
    One alignment-validation issue.
    """

    page_number: int

    code: AlignmentValidationCode

    severity: AlignmentValidationSeverity

    message: str

    paragraph_region_number: int | None = None

    metrics: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(slots=True)
class AlignmentPageValidationSummary:
    """
    Alignment-validation summary for one page.
    """

    page_number: int

    paragraph_count: int = 0
    result_count: int = 0

    alignment_counts: dict[str, int] = field(
        default_factory=dict
    )

    reference_counts: dict[str, int] = field(
        default_factory=dict
    )

    average_confidence: float = 0.0
    minimum_confidence: float = 0.0

    low_confidence_count: int = 0
    unknown_count: int = 0

    warning_count: int = 0
    error_count: int = 0

    passed: bool = True


@dataclass(slots=True)
class AlignmentValidationReport:
    """
    Complete alignment-validation report for a document.
    """

    page_count: int = 0

    paragraph_count: int = 0
    result_count: int = 0

    alignment_counts: dict[str, int] = field(
        default_factory=dict
    )

    reference_counts: dict[str, int] = field(
        default_factory=dict
    )

    average_confidence: float = 0.0
    minimum_confidence: float = 0.0

    low_confidence_count: int = 0
    unknown_count: int = 0

    warning_count: int = 0
    error_count: int = 0

    passed: bool = True

    page_summaries: list[
        AlignmentPageValidationSummary
    ] = field(
        default_factory=list
    )

    issues: list[
        AlignmentValidationIssue
    ] = field(
        default_factory=list
    )

    def add_issue(
        self,
        issue: AlignmentValidationIssue,
    ) -> None:
        self.issues.append(
            issue
        )

        if (
            issue.severity
            == AlignmentValidationSeverity.ERROR
        ):
            self.error_count += 1
            self.passed = False

        elif (
            issue.severity
            == AlignmentValidationSeverity.WARNING
        ):
            self.warning_count += 1