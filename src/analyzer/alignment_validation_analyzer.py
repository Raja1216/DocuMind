from __future__ import annotations

from collections import Counter
from statistics import fmean
from typing import Any

from src.models.alignment_validation import (
    AlignmentPageValidationSummary,
    AlignmentValidationCode,
    AlignmentValidationIssue,
    AlignmentValidationReport,
    AlignmentValidationSeverity,
)
from src.models.document import Document
from src.models.page import Page
from src.models.paragraph_alignment import (
    AlignmentReferenceType,
    ParagraphAlignment,
    ParagraphAlignmentResult,
)
from src.models.reading_order import (
    ReadingOrderRole,
)
from src.utils.rectangle_union import (
    Bounds,
    RectangleUnion,
)


class AlignmentValidationAnalyzer:
    """
    Validates alignment results before they are used by the
    editable DOCX exporter.

    Validation checks geometry and container consistency. It
    does not recalculate paragraph alignment.
    """

    MINIMUM_ACCEPTED_CONFIDENCE = 0.55

    MINIMUM_CENTER_TOLERANCE = 8.0
    CENTER_OFFSET_TOLERANCE_RATIO = 0.06
    CENTER_GAP_IMBALANCE_RATIO = 0.10

    MINIMUM_EDGE_GAP_TOLERANCE = 10.0
    SIDE_EDGE_GAP_TOLERANCE_RATIO = 0.08

    SIDE_GAP_DOMINANCE_RATIO = 1.50

    JUSTIFY_MINIMUM_LINE_COUNT = 2
    JUSTIFY_MAXIMUM_LAST_LINE_RELATIVE_WIDTH = 0.98
    JUSTIFY_MAXIMUM_LAST_LINE_WIDTH_RATIO = 0.95

    REFERENCE_CONTAINMENT_TOLERANCE = 8.0

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> AlignmentValidationReport:
        """
        Validate all pages and attach a fresh report.
        """

        report = AlignmentValidationReport(
            page_count=len(
                document.pages
            )
        )

        document.alignment_validation_report = (
            report
        )

        all_confidences: list[float] = []

        alignment_counter: Counter[str] = (
            Counter()
        )

        reference_counter: Counter[str] = (
            Counter()
        )

        for page in document.pages:
            page_summary = cls._analyze_page(
                page=page,
                report=report,
            )

            report.page_summaries.append(
                page_summary
            )

            report.paragraph_count += (
                page_summary.paragraph_count
            )

            report.result_count += (
                page_summary.result_count
            )

            report.low_confidence_count += (
                page_summary
                .low_confidence_count
            )

            report.unknown_count += (
                page_summary.unknown_count
            )

            alignment_counter.update(
                page_summary.alignment_counts
            )

            reference_counter.update(
                page_summary.reference_counts
            )

            all_confidences.extend([
                result.confidence
                for result in (
                    page
                    .paragraph_alignment_results
                )
            ])

        report.alignment_counts = dict(
            sorted(
                alignment_counter.items()
            )
        )

        report.reference_counts = dict(
            sorted(
                reference_counter.items()
            )
        )

        if all_confidences:
            report.average_confidence = (
                fmean(
                    all_confidences
                )
            )

            report.minimum_confidence = min(
                all_confidences
            )

        report.passed = (
            report.error_count == 0
        )

        return report

    @classmethod
    def _analyze_page(
        cls,
        page: Page,
        report: AlignmentValidationReport,
    ) -> AlignmentPageValidationSummary:
        """
        Validate one page.
        """

        paragraph_numbers = (
            cls._collect_visible_paragraph_numbers(
                page
            )
        )

        results = list(
            getattr(
                page,
                "paragraph_alignment_results",
                [],
            )
            or []
        )

        summary = AlignmentPageValidationSummary(
            page_number=page.number,
            paragraph_count=len(
                paragraph_numbers
            ),
            result_count=len(
                results
            ),
        )

        result_number_counter = Counter(
            result.paragraph_region_number
            for result in results
        )

        duplicate_numbers = {
            paragraph_number
            for (
                paragraph_number,
                count,
            ) in result_number_counter.items()
            if count > 1
        }

        for paragraph_number in sorted(
            duplicate_numbers
        ):
            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        paragraph_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .DUPLICATE_RESULT
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .ERROR
                    ),
                    message=(
                        "Multiple alignment results exist "
                        "for the same paragraph."
                    ),
                ),
            )

        result_by_number = {}

        for result in results:
            result_by_number.setdefault(
                result.paragraph_region_number,
                result,
            )

        paragraph_number_set = set(
            paragraph_numbers
        )

        result_number_set = set(
            result_by_number
        )

        missing_numbers = (
            paragraph_number_set
            - result_number_set
        )

        extra_numbers = (
            result_number_set
            - paragraph_number_set
        )

        for paragraph_number in sorted(
            missing_numbers
        ):
            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        paragraph_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .MISSING_RESULT
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .ERROR
                    ),
                    message=(
                        "Visible paragraph has no "
                        "alignment result."
                    ),
                ),
            )

        for paragraph_number in sorted(
            extra_numbers
        ):
            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        paragraph_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .EXTRA_RESULT
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .WARNING
                    ),
                    message=(
                        "Alignment result does not match "
                        "a visible paragraph."
                    ),
                ),
            )

        alignment_counter = Counter(
            result.alignment.value
            for result in results
        )

        reference_counter = Counter(
            result.reference_type.value
            for result in results
        )

        summary.alignment_counts = dict(
            sorted(
                alignment_counter.items()
            )
        )

        summary.reference_counts = dict(
            sorted(
                reference_counter.items()
            )
        )

        confidences = [
            result.confidence
            for result in results
        ]

        if confidences:
            summary.average_confidence = (
                fmean(
                    confidences
                )
            )

            summary.minimum_confidence = min(
                confidences
            )

        role_by_paragraph = {
            entry.paragraph_region_number: (
                entry.role
            )
            for entry in getattr(
                page,
                "reading_order_entries",
                [],
            )
        }

        paragraph_by_number = (
            cls._paragraphs_by_number(
                page
            )
        )

        for result in results:
            paragraph_number = (
                result.paragraph_region_number
            )

            paragraph = (
                paragraph_by_number.get(
                    paragraph_number
                )
            )

            role = role_by_paragraph.get(
                paragraph_number
            )

            cls._validate_one_result(
                page=page,
                paragraph=paragraph,
                role=role,
                result=result,
                report=report,
                summary=summary,
            )

        summary.passed = (
            summary.error_count == 0
        )

        return summary

    @classmethod
    def _validate_one_result(
        cls,
        page: Page,
        paragraph: Any | None,
        role: ReadingOrderRole | None,
        result: ParagraphAlignmentResult,
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
    ) -> None:
        paragraph_number = (
            result.paragraph_region_number
        )

        if (
            result.alignment
            == ParagraphAlignment.UNKNOWN
        ):
            summary.unknown_count += 1

            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        paragraph_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .UNKNOWN_ALIGNMENT
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .WARNING
                    ),
                    message=(
                        "Paragraph alignment could not "
                        "be classified reliably."
                    ),
                    metrics=(
                        cls._result_metrics(
                            result
                        )
                    ),
                ),
            )

        if (
            result.confidence
            < cls.MINIMUM_ACCEPTED_CONFIDENCE
        ):
            summary.low_confidence_count += 1

            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        paragraph_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .LOW_CONFIDENCE
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .WARNING
                    ),
                    message=(
                        "Alignment confidence is below "
                        "the exporter safety threshold."
                    ),
                    metrics={
                        "confidence": (
                            result.confidence
                        ),
                        "minimum_required": (
                            cls
                            .MINIMUM_ACCEPTED_CONFIDENCE
                        ),
                    },
                ),
            )

        cls._validate_reference(
            page=page,
            paragraph=paragraph,
            role=role,
            result=result,
            report=report,
            summary=summary,
        )

        cls._validate_geometry(
            page=page,
            result=result,
            report=report,
            summary=summary,
        )

        cls._validate_reference_containment(
            page=page,
            result=result,
            report=report,
            summary=summary,
        )

    # ---------------------------------------------------------
    # Reference validation
    # ---------------------------------------------------------

    @classmethod
    def _validate_reference(
        cls,
        page: Page,
        paragraph: Any | None,
        role: ReadingOrderRole | None,
        result: ParagraphAlignmentResult,
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
    ) -> None:
        expected_reference: (
            AlignmentReferenceType
            | None
        ) = None

        if role == ReadingOrderRole.HEADER:
            expected_reference = (
                AlignmentReferenceType.HEADER
            )

        elif role == ReadingOrderRole.FOOTER:
            expected_reference = (
                AlignmentReferenceType.FOOTER
            )

        elif role == ReadingOrderRole.COLUMN:
            expected_reference = (
                AlignmentReferenceType.COLUMN
            )

        elif (
            role
            == ReadingOrderRole.BODY_SPANNING
        ):
            expected_reference = (
                AlignmentReferenceType.PAGE_BODY
            )

        explicit_column_id = (
            getattr(
                paragraph,
                "column_id",
                None,
            )
            if paragraph is not None
            else None
        )

        if (
            len(
                getattr(
                    page,
                    "column_regions",
                    [],
                )
            )
            >= 2
            and explicit_column_id is not None
        ):
            expected_reference = (
                AlignmentReferenceType.COLUMN
            )

        if (
            expected_reference is not None
            and result.reference_type
            != expected_reference
        ):
            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        result
                        .paragraph_region_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .REFERENCE_MISMATCH
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .WARNING
                    ),
                    message=(
                        "Paragraph alignment was measured "
                        "against an unexpected container."
                    ),
                    metrics={
                        "expected_reference": (
                            expected_reference.value
                        ),
                        "actual_reference": (
                            result
                            .reference_type
                            .value
                        ),
                        "reference_id": (
                            result.reference_id
                        ),
                    },
                ),
            )

    # ---------------------------------------------------------
    # Geometry validation
    # ---------------------------------------------------------

    @classmethod
    def _validate_geometry(
        cls,
        page: Page,
        result: ParagraphAlignmentResult,
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
    ) -> None:
        reference_width = (
            result.reference_width
        )

        if reference_width <= 0.0:
            return

        center_tolerance = max(
            cls.MINIMUM_CENTER_TOLERANCE,
            reference_width
            * cls
            .CENTER_OFFSET_TOLERANCE_RATIO,
        )

        center_gap_tolerance = max(
            cls.MINIMUM_CENTER_TOLERANCE,
            reference_width
            * cls
            .CENTER_GAP_IMBALANCE_RATIO,
        )

        edge_gap_tolerance = max(
            cls.MINIMUM_EDGE_GAP_TOLERANCE,
            reference_width
            * cls
            .SIDE_EDGE_GAP_TOLERANCE_RATIO,
        )

        if (
            result.alignment
            == ParagraphAlignment.CENTER
        ):
            gap_difference = abs(
                result.left_gap
                - result.right_gap
            )

            if (
                result.absolute_center_offset
                > center_tolerance
                or gap_difference
                > center_gap_tolerance
            ):
                cls._geometry_issue(
                    page=page,
                    result=result,
                    report=report,
                    summary=summary,
                    code=(
                        AlignmentValidationCode
                        .CENTER_GEOMETRY_CONFLICT
                    ),
                    message=(
                        "Centered alignment conflicts "
                        "with container-relative geometry."
                    ),
                )

        elif (
            result.alignment
            == ParagraphAlignment.RIGHT
        ):
            right_conflict = (
                result.right_gap
                > edge_gap_tolerance
                or result.left_gap
                <= result.right_gap
            )

            if right_conflict:
                cls._geometry_issue(
                    page=page,
                    result=result,
                    report=report,
                    summary=summary,
                    code=(
                        AlignmentValidationCode
                        .RIGHT_GEOMETRY_CONFLICT
                    ),
                    message=(
                        "Right alignment conflicts with "
                        "the paragraph's edge gaps."
                    ),
                )

        elif (
            result.alignment
            == ParagraphAlignment.LEFT
        ):
            appears_right_anchored = (
                result.right_gap
                <= edge_gap_tolerance
                and result.left_gap
                > (
                    result.right_gap
                    * cls
                    .SIDE_GAP_DOMINANCE_RATIO
                )
                and not result.has_hanging_indent
            )

            if appears_right_anchored:
                cls._geometry_issue(
                    page=page,
                    result=result,
                    report=report,
                    summary=summary,
                    code=(
                        AlignmentValidationCode
                        .LEFT_GEOMETRY_CONFLICT
                    ),
                    message=(
                        "Left alignment appears to be "
                        "right-anchored geometrically."
                    ),
                )

        elif (
            result.alignment
            == ParagraphAlignment.JUSTIFY
        ):
            justify_conflict = (
                result.line_count
                < cls.JUSTIFY_MINIMUM_LINE_COUNT
                or (
                    result.last_line_relative_width
                    > cls
                    .JUSTIFY_MAXIMUM_LAST_LINE_RELATIVE_WIDTH
                    and result.last_line_width_ratio
                    > cls
                    .JUSTIFY_MAXIMUM_LAST_LINE_WIDTH_RATIO
                )
            )

            if justify_conflict:
                cls._geometry_issue(
                    page=page,
                    result=result,
                    report=report,
                    summary=summary,
                    code=(
                        AlignmentValidationCode
                        .JUSTIFY_GEOMETRY_CONFLICT
                    ),
                    message=(
                        "Justified alignment lacks the "
                        "expected multi-line geometry."
                    ),
                )

    @classmethod
    def _geometry_issue(
        cls,
        page: Page,
        result: ParagraphAlignmentResult,
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
        code: AlignmentValidationCode,
        message: str,
    ) -> None:
        cls._add_issue(
            report=report,
            summary=summary,
            issue=AlignmentValidationIssue(
                page_number=page.number,
                paragraph_region_number=(
                    result.paragraph_region_number
                ),
                code=code,
                severity=(
                    AlignmentValidationSeverity
                    .WARNING
                ),
                message=message,
                metrics=cls._result_metrics(
                    result
                ),
            ),
        )

    # ---------------------------------------------------------
    # Containment validation
    # ---------------------------------------------------------

    @classmethod
    def _validate_reference_containment(
        cls,
        page: Page,
        result: ParagraphAlignmentResult,
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
    ) -> None:
        paragraph_bbox = (
            RectangleUnion
            .normalize_rectangle(
                result.paragraph_bbox
            )
        )

        reference_bbox = (
            RectangleUnion
            .normalize_rectangle(
                result.reference_bbox
            )
        )

        if (
            paragraph_bbox is None
            or reference_bbox is None
        ):
            return

        tolerance = (
            cls.REFERENCE_CONTAINMENT_TOLERANCE
        )

        outside = any([
            paragraph_bbox[0]
            < reference_bbox[0] - tolerance,

            paragraph_bbox[1]
            < reference_bbox[1] - tolerance,

            paragraph_bbox[2]
            > reference_bbox[2] + tolerance,

            paragraph_bbox[3]
            > reference_bbox[3] + tolerance,
        ])

        if outside:
            cls._add_issue(
                report=report,
                summary=summary,
                issue=AlignmentValidationIssue(
                    page_number=page.number,
                    paragraph_region_number=(
                        result
                        .paragraph_region_number
                    ),
                    code=(
                        AlignmentValidationCode
                        .PARAGRAPH_OUTSIDE_REFERENCE
                    ),
                    severity=(
                        AlignmentValidationSeverity
                        .WARNING
                    ),
                    message=(
                        "Paragraph geometry extends "
                        "outside its alignment reference."
                    ),
                    metrics={
                        "paragraph_bbox": (
                            paragraph_bbox
                        ),
                        "reference_bbox": (
                            reference_bbox
                        ),
                    },
                ),
            )

    # ---------------------------------------------------------
    # Paragraph preparation
    # ---------------------------------------------------------

    @classmethod
    def _collect_visible_paragraph_numbers(
        cls,
        page: Page,
    ) -> list[int]:
        paragraph_numbers: list[int] = []

        used_numbers: set[int] = set()

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    paragraph
                )
            )

            if bbox is None:
                continue

            paragraph_number = (
                cls._resolve_paragraph_number(
                    paragraph=paragraph,
                    fallback=index + 1,
                )
            )

            while paragraph_number in used_numbers:
                paragraph_number += 1

            used_numbers.add(
                paragraph_number
            )

            paragraph_numbers.append(
                paragraph_number
            )

        return paragraph_numbers

    @classmethod
    def _paragraphs_by_number(
        cls,
        page: Page,
    ) -> dict[int, Any]:
        result: dict[int, Any] = {}

        used_numbers: set[int] = set()

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    paragraph
                )
            )

            if bbox is None:
                continue

            paragraph_number = (
                cls._resolve_paragraph_number(
                    paragraph=paragraph,
                    fallback=index + 1,
                )
            )

            while paragraph_number in used_numbers:
                paragraph_number += 1

            used_numbers.add(
                paragraph_number
            )

            result[
                paragraph_number
            ] = paragraph

        return result

    @staticmethod
    def _resolve_paragraph_number(
        paragraph: Any,
        fallback: int,
    ) -> int:
        raw_number = getattr(
            paragraph,
            "region_number",
            fallback,
        )

        try:
            return int(
                raw_number
            )

        except (
            TypeError,
            ValueError,
        ):
            return fallback

    # ---------------------------------------------------------
    # Issue and metric helpers
    # ---------------------------------------------------------

    @staticmethod
    def _add_issue(
        report: AlignmentValidationReport,
        summary: AlignmentPageValidationSummary,
        issue: AlignmentValidationIssue,
    ) -> None:
        report.add_issue(
            issue
        )

        if (
            issue.severity
            == AlignmentValidationSeverity.ERROR
        ):
            summary.error_count += 1
            summary.passed = False

        elif (
            issue.severity
            == AlignmentValidationSeverity.WARNING
        ):
            summary.warning_count += 1

    @staticmethod
    def _result_metrics(
        result: ParagraphAlignmentResult,
    ) -> dict[str, Any]:
        return {
            "alignment": (
                result.alignment.value
            ),
            "confidence": (
                result.confidence
            ),
            "reference_type": (
                result.reference_type.value
            ),
            "reference_id": (
                result.reference_id
            ),
            "left_gap": (
                result.left_gap
            ),
            "right_gap": (
                result.right_gap
            ),
            "center_offset": (
                result.center_offset
            ),
            "width_ratio": (
                result.width_ratio
            ),
            "line_count": (
                result.line_count
            ),
            "last_line_width_ratio": (
                result.last_line_width_ratio
            ),
            "last_line_relative_width": (
                result
                .last_line_relative_width
            ),
            "has_hanging_indent": (
                result.has_hanging_indent
            ),
        }