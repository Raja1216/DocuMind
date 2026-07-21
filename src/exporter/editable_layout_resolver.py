from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
)
from docx.text.paragraph import Paragraph

from src.models.alignment_validation import (
    AlignmentValidationCode,
    AlignmentValidationReport,
)
from src.models.page import Page
from src.models.paragraph_alignment import (
    ParagraphAlignment,
    ParagraphAlignmentResult,
)
from src.models.reading_order import (
    ReadingOrderEntry,
    ReadingOrderRole,
)
from src.utils.rectangle_union import (
    RectangleUnion,
)


@dataclass(slots=True)
class EditableParagraphPlan:
    """
    Describes how one ParagraphRegion should be exported.

    It combines:

        reading order;
        reading-order role;
        validated PDF alignment;
        Word alignment.
    """

    page_number: int

    paragraph_region_number: int

    paragraph: Any

    reading_order: int

    role: ReadingOrderRole

    detected_alignment: ParagraphAlignment

    alignment_confidence: float

    word_alignment: (
        WD_ALIGN_PARAGRAPH | None
    )

    apply_alignment: bool

    reason: str


@dataclass(slots=True)
class _ParagraphRecord:
    """
    Internal normalized paragraph record.

    The effective number calculation matches the reading-order
    and alignment analyzers, including duplicate-number
    handling.
    """

    number: int

    original_index: int

    paragraph: Any

    top: float

    left: float


class EditableLayoutResolver:
    """
    Creates a safe editable-DOCX export plan.

    Reading order is used whenever it is available.

    Detected alignment is used only when:

        the alignment is known;
        confidence passes the safety threshold;
        validation found no blocking issue.
    """

    MINIMUM_ALIGNMENT_CONFIDENCE = 0.55

    BLOCKING_VALIDATION_CODES = {
        AlignmentValidationCode.MISSING_RESULT,
        AlignmentValidationCode.DUPLICATE_RESULT,

        AlignmentValidationCode.REFERENCE_MISMATCH,

        AlignmentValidationCode.PARAGRAPH_OUTSIDE_REFERENCE,

        AlignmentValidationCode.CENTER_GEOMETRY_CONFLICT,
        AlignmentValidationCode.RIGHT_GEOMETRY_CONFLICT,
        AlignmentValidationCode.LEFT_GEOMETRY_CONFLICT,
        AlignmentValidationCode.JUSTIFY_GEOMETRY_CONFLICT,
    }

    WORD_ALIGNMENT_MAP = {
        ParagraphAlignment.LEFT: (
            WD_ALIGN_PARAGRAPH.LEFT
        ),

        ParagraphAlignment.CENTER: (
            WD_ALIGN_PARAGRAPH.CENTER
        ),

        ParagraphAlignment.RIGHT: (
            WD_ALIGN_PARAGRAPH.RIGHT
        ),

        ParagraphAlignment.JUSTIFY: (
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ),
    }

    @classmethod
    def build_page_plan(
        cls,
        page: Page,
        validation_report: (
            AlignmentValidationReport | None
        ) = None,
    ) -> list[EditableParagraphPlan]:
        """
        Build the ordered editable-export plan for one page.

        Paragraphs not present in ReadingOrderEntry are appended
        safely instead of being discarded.
        """

        paragraph_records = (
            cls._collect_paragraph_records(
                page
            )
        )

        if not paragraph_records:
            return []

        record_by_number = {
            record.number: record
            for record in paragraph_records
        }

        alignment_by_number = {
            result.paragraph_region_number: result
            for result in getattr(
                page,
                "paragraph_alignment_results",
                [],
            )
            or []
        }

        issue_index = (
            cls._build_issue_index(
                validation_report
            )
        )

        reading_entries = sorted(
            getattr(
                page,
                "reading_order_entries",
                [],
            )
            or [],
            key=lambda entry: (
                entry.order,
                entry.paragraph_region_number,
            ),
        )

        plan: list[
            EditableParagraphPlan
        ] = []

        consumed_numbers: set[int] = set()

        maximum_reading_order = 0

        for entry in reading_entries:
            paragraph_number = (
                entry.paragraph_region_number
            )

            if paragraph_number in consumed_numbers:
                continue

            record = record_by_number.get(
                paragraph_number
            )

            if record is None:
                continue

            maximum_reading_order = max(
                maximum_reading_order,
                int(entry.order),
            )

            plan.append(
                cls._create_plan_item(
                    page=page,
                    record=record,
                    reading_order=int(
                        entry.order
                    ),
                    role=entry.role,
                    alignment_result=(
                        alignment_by_number.get(
                            paragraph_number
                        )
                    ),
                    issue_codes=issue_index.get(
                        (
                            page.number,
                            paragraph_number,
                        ),
                        set(),
                    ),
                )
            )

            consumed_numbers.add(
                paragraph_number
            )

        # Never lose paragraphs when reading-order analysis was
        # incomplete or a paragraph was intentionally unassigned.
        remaining_records = [
            record
            for record in paragraph_records
            if record.number not in consumed_numbers
        ]

        remaining_records.sort(
            key=lambda record: (
                cls._paragraph_reading_order(
                    record.paragraph
                ),
                record.top,
                record.left,
                record.original_index,
            )
        )

        next_order = (
            maximum_reading_order + 1
        )

        for record in remaining_records:
            plan.append(
                cls._create_plan_item(
                    page=page,
                    record=record,
                    reading_order=next_order,
                    role=(
                        ReadingOrderRole.UNASSIGNED
                    ),
                    alignment_result=(
                        alignment_by_number.get(
                            record.number
                        )
                    ),
                    issue_codes=issue_index.get(
                        (
                            page.number,
                            record.number,
                        ),
                        set(),
                    ),
                )
            )

            next_order += 1

        plan.sort(
            key=lambda item: (
                item.reading_order,
                item.paragraph_region_number,
            )
        )

        return plan

    @classmethod
    def apply_alignment(
        cls,
        word_paragraph: Paragraph,
        plan: EditableParagraphPlan,
    ) -> None:
        """
        Apply validated alignment to a python-docx paragraph.

        When apply_alignment is False, no alignment property is
        written. Microsoft Word then uses the document/style
        default, normally left alignment.
        """

        if (
            not plan.apply_alignment
            or plan.word_alignment is None
        ):
            return

        word_paragraph.alignment = (
            plan.word_alignment
        )

    @classmethod
    def _create_plan_item(
        cls,
        page: Page,
        record: _ParagraphRecord,
        reading_order: int,
        role: ReadingOrderRole,
        alignment_result: (
            ParagraphAlignmentResult | None
        ),
        issue_codes: set[
            AlignmentValidationCode
        ],
    ) -> EditableParagraphPlan:
        if alignment_result is None:
            detected_alignment = (
                cls._paragraph_alignment(
                    record.paragraph
                )
            )

            alignment_confidence = (
                cls._paragraph_alignment_confidence(
                    record.paragraph
                )
            )

        else:
            detected_alignment = (
                alignment_result.alignment
            )

            alignment_confidence = (
                float(
                    alignment_result.confidence
                )
            )

        (
            word_alignment,
            apply_alignment,
            reason,
        ) = cls._resolve_word_alignment(
            detected_alignment=(
                detected_alignment
            ),
            confidence=(
                alignment_confidence
            ),
            issue_codes=issue_codes,
        )

        return EditableParagraphPlan(
            page_number=page.number,

            paragraph_region_number=(
                record.number
            ),

            paragraph=record.paragraph,

            reading_order=reading_order,

            role=role,

            detected_alignment=(
                detected_alignment
            ),

            alignment_confidence=(
                alignment_confidence
            ),

            word_alignment=word_alignment,

            apply_alignment=apply_alignment,

            reason=reason,
        )

    @classmethod
    def _resolve_word_alignment(
        cls,
        detected_alignment: ParagraphAlignment,
        confidence: float,
        issue_codes: set[
            AlignmentValidationCode
        ],
    ) -> tuple[
        WD_ALIGN_PARAGRAPH | None,
        bool,
        str,
    ]:
        """
        Resolve safe Word alignment.
        """

        blocking_codes = (
            issue_codes
            & cls.BLOCKING_VALIDATION_CODES
        )

        if blocking_codes:
            formatted_codes = ", ".join(
                sorted(
                    code.value
                    for code in blocking_codes
                )
            )

            return (
                None,
                False,
                (
                    "Alignment was not applied because "
                    "validation reported: "
                    f"{formatted_codes}."
                ),
            )

        if (
            detected_alignment
            == ParagraphAlignment.UNKNOWN
        ):
            return (
                None,
                False,
                (
                    "Alignment is unknown; Word default "
                    "alignment is preserved."
                ),
            )

        if (
            confidence
            < cls.MINIMUM_ALIGNMENT_CONFIDENCE
        ):
            return (
                None,
                False,
                (
                    "Alignment confidence is below the "
                    "editable-export safety threshold."
                ),
            )

        word_alignment = (
            cls.WORD_ALIGNMENT_MAP.get(
                detected_alignment
            )
        )

        if word_alignment is None:
            return (
                None,
                False,
                (
                    "No Word alignment mapping exists for "
                    "the detected alignment."
                ),
            )

        return (
            word_alignment,
            True,
            (
                "Validated container-aware alignment was "
                "applied to the Word paragraph."
            ),
        )

    @classmethod
    def _collect_paragraph_records(
        cls,
        page: Page,
    ) -> list[_ParagraphRecord]:
        records: list[
            _ParagraphRecord
        ] = []

        used_numbers: set[int] = set()

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
            if getattr(
                paragraph,
                "is_list_marker_only",
                False,
            ):
                continue
            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            raw_number = getattr(
                paragraph,
                "region_number",
                index + 1,
            )

            try:
                paragraph_number = int(
                    raw_number
                )

            except (
                TypeError,
                ValueError,
            ):
                paragraph_number = index + 1

            while paragraph_number in used_numbers:
                paragraph_number += 1

            used_numbers.add(
                paragraph_number
            )

            bbox = (
                RectangleUnion
                .normalize_rectangle(
                    paragraph
                )
            )

            if bbox is None:
                top = float(index)
                left = 0.0

            else:
                left = bbox[0]
                top = bbox[1]

            records.append(
                _ParagraphRecord(
                    number=paragraph_number,

                    original_index=index,

                    paragraph=paragraph,

                    top=top,

                    left=left,
                )
            )

        return records

    @staticmethod
    def _build_issue_index(
        validation_report: (
            AlignmentValidationReport | None
        ),
    ) -> dict[
        tuple[int, int],
        set[AlignmentValidationCode],
    ]:
        issue_index: dict[
            tuple[int, int],
            set[AlignmentValidationCode],
        ] = {}

        if validation_report is None:
            return issue_index

        for issue in validation_report.issues:
            paragraph_number = (
                issue.paragraph_region_number
            )

            if paragraph_number is None:
                continue

            key = (
                issue.page_number,
                paragraph_number,
            )

            issue_index.setdefault(
                key,
                set(),
            ).add(
                issue.code
            )

        return issue_index

    @staticmethod
    def _paragraph_reading_order(
        paragraph: Any,
    ) -> int:
        raw_value = getattr(
            paragraph,
            "reading_order",
            None,
        )

        try:
            if raw_value is not None:
                return int(
                    raw_value
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

        return 1_000_000

    @staticmethod
    def _paragraph_alignment(
        paragraph: Any,
    ) -> ParagraphAlignment:
        value = getattr(
            paragraph,
            "detected_alignment",
            ParagraphAlignment.UNKNOWN,
        )

        if isinstance(
            value,
            ParagraphAlignment,
        ):
            return value

        try:
            return ParagraphAlignment(
                str(value)
            )

        except ValueError:
            return ParagraphAlignment.UNKNOWN

    @staticmethod
    def _paragraph_alignment_confidence(
        paragraph: Any,
    ) -> float:
        try:
            return float(
                getattr(
                    paragraph,
                    "alignment_confidence",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0