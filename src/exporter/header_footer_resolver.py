from __future__ import annotations

import re

from dataclasses import dataclass, field

from src.exporter.editable_layout_resolver import (
    EditableLayoutResolver,
    EditableParagraphPlan,
)
from src.models.reading_order import (
    ReadingOrderRole,
)


@dataclass(slots=True)
class PageNumberFieldPlan:
    """
    Describes a page-number paragraph that should become
    Word PAGE and optionally NUMPAGES fields.
    """

    paragraph_region_number: int

    prefix: str = ""
    separator: str = ""
    suffix: str = ""

    include_total_pages: bool = False


@dataclass(slots=True)
class HeaderFooterExportPlan:
    """
    Header/footer paragraphs selected for one Word section.
    """

    header_plans: list[
        EditableParagraphPlan
    ] = field(
        default_factory=list
    )

    footer_plans: list[
        EditableParagraphPlan
    ] = field(
        default_factory=list
    )

    page_number_fields: dict[
        int,
        PageNumberFieldPlan,
    ] = field(
        default_factory=dict
    )


class HeaderFooterResolver:
    """
    Converts detected header/footer reading-order entries into
    a section-level Word export plan.
    """

    PAGE_NUMBER_PATTERN = re.compile(
        r"""
        ^
        \s*
        (?P<prefix>page\s*)?
        (?P<current>\d+)
        (?:
            (?P<separator>
                \s*
                (?:
                    of
                    |
                    /
                )
                \s*
            )
            (?P<total>\d+)
        )?
        (?P<suffix>\s*)
        $
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    @classmethod
    def build(
        cls,
        page,
        validation_report=None,
    ) -> HeaderFooterExportPlan:
        paragraph_plans = (
            EditableLayoutResolver
            .build_page_plan(
                page=page,
                validation_report=(
                    validation_report
                ),
            )
        )

        result = HeaderFooterExportPlan()

        for paragraph_plan in paragraph_plans:
            if (
                paragraph_plan.role
                == ReadingOrderRole.HEADER
            ):
                result.header_plans.append(
                    paragraph_plan
                )

            elif (
                paragraph_plan.role
                == ReadingOrderRole.FOOTER
            ):
                result.footer_plans.append(
                    paragraph_plan
                )

            else:
                continue

            field_plan = (
                cls._parse_page_number_field(
                    paragraph_plan
                )
            )

            if field_plan is not None:
                result.page_number_fields[
                    paragraph_plan
                    .paragraph_region_number
                ] = field_plan

        return result

    @classmethod
    def section_signature(
        cls,
        page,
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
    ]:
        """
        Return a stable header/footer signature.

        Dynamic page numbers are normalized, allowing pages
        with footer numbers 1, 2, 3... to share one section.
        """

        paragraph_by_number = {}

        for index, paragraph in enumerate(
            getattr(
                page,
                "paragraph_regions",
                [],
            )
            or []
        ):
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
                paragraph_number = (
                    index + 1
                )

            paragraph_by_number[
                paragraph_number
            ] = paragraph

        header_values: list[str] = []
        footer_values: list[str] = []

        entries = sorted(
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

        for entry in entries:
            paragraph = paragraph_by_number.get(
                entry.paragraph_region_number
            )

            if paragraph is None:
                continue

            text = str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).strip()

            normalized_text = (
                cls._normalize_signature_text(
                    text
                )
            )

            if (
                entry.role
                == ReadingOrderRole.HEADER
            ):
                header_values.append(
                    normalized_text
                )

            elif (
                entry.role
                == ReadingOrderRole.FOOTER
            ):
                footer_values.append(
                    normalized_text
                )

        return (
            tuple(
                header_values
            ),
            tuple(
                footer_values
            ),
        )

    @classmethod
    def _parse_page_number_field(
        cls,
        paragraph_plan: EditableParagraphPlan,
    ) -> PageNumberFieldPlan | None:
        text = str(
            getattr(
                paragraph_plan.paragraph,
                "text",
                "",
            )
        ).strip()

        match = cls.PAGE_NUMBER_PATTERN.fullmatch(
            text
        )

        if match is None:
            return None

        prefix = (
            match.group(
                "prefix"
            )
            or ""
        )

        separator = (
            match.group(
                "separator"
            )
            or ""
        )

        suffix = (
            match.group(
                "suffix"
            )
            or ""
        )

        return PageNumberFieldPlan(
            paragraph_region_number=(
                paragraph_plan
                .paragraph_region_number
            ),
            prefix=prefix,
            separator=separator,
            suffix=suffix,
            include_total_pages=(
                match.group(
                    "total"
                )
                is not None
            ),
        )

    @classmethod
    def _normalize_signature_text(
        cls,
        text: str,
    ) -> str:
        normalized = " ".join(
            text.split()
        ).strip()

        if cls.PAGE_NUMBER_PATTERN.fullmatch(
            normalized
        ):
            return "__word_page_field__"

        return normalized.casefold()