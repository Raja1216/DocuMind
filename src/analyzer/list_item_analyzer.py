from __future__ import annotations

import re

from dataclasses import dataclass
from typing import Any

from src.models.document import Document
from src.models.list_item import (
    ListItemResult,
    ListMarkerKind,
    ListMarkerSource,
)
from src.models.page import Page


@dataclass(slots=True)
class _MarkerMatch:
    marker: str
    list_type: str
    marker_kind: ListMarkerKind
    confidence: float


class ListItemAnalyzer:
    """
    Detects and normalizes list markers.

    This analyzer handles:

        textual bullets;
        textual numbering;
        alphabetic numbering;
        Roman numbering;
        multilevel decimal numbering;
        previously attached vector bullets.

    Sequence grouping and nesting are intentionally deferred to
    Step 62.9G.2.
    """

    BULLET_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<marker>
            [•◦▪▫●○■□‣⁃⁌⁍➢➤➔✓✔]
        )
        (?:\s+|$)
        """,
        flags=re.VERBOSE,
    )

    NUMBER_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<marker>
            (?:
                \(
                    \s*
                    (?:
                        \d+(?:\.\d+)*
                        |
                        [A-Za-z]
                        |
                        [ivxlcdmIVXLCDM]+
                    )
                    \s*
                \)
                |
                (?:
                    \d+(?:\.\d+)*
                    |
                    [A-Za-z]
                    |
                    [ivxlcdmIVXLCDM]+
                )
                [\.\)]
            )
        )
        (?:\s+|$)
        """,
        flags=re.VERBOSE,
    )

    ROMAN_PATTERN = re.compile(
        r"^[ivxlcdm]+$",
        flags=re.IGNORECASE,
    )

    DECIMAL_PATTERN = re.compile(
        r"^\d+$"
    )

    MULTILEVEL_DECIMAL_PATTERN = re.compile(
        r"^\d+(?:\.\d+)+$"
    )

    ESTIMATED_CHARACTER_WIDTH_FACTOR = 0.48
    MINIMUM_MARKER_CONTENT_GAP = 4.0
    
    STANDALONE_MARKER_MAXIMUM_GAP = 72.0

    STANDALONE_MARKER_MINIMUM_VERTICAL_OVERLAP = (
        0.45
    )

    STANDALONE_MARKER_MAXIMUM_CENTER_OFFSET = 8.0

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> None:
        for page in document.pages:
            cls.analyze_page(
                page
            )

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> list[ListItemResult]:
        """
        Rebuild list-item results for one page.
        """

        page.list_item_results.clear()

        for paragraph in (
            page.paragraph_regions
        ):
            cls._analyze_paragraph(
                page=page,
                paragraph=paragraph,
            )

        # Some PDFs extract the marker and text as separate
        # ParagraphRegions even though they are visually on the same
        # line. Transfer the marker metadata to the content paragraph.
        cls._attach_standalone_markers(
            page
        )

        return page.list_item_results

    @classmethod
    def _analyze_paragraph(
        cls,
        page: Page,
        paragraph: Any,
    ) -> None:
        existing_type = getattr(
            paragraph,
            "list_type",
            None,
        )

        existing_marker = getattr(
            paragraph,
            "list_marker",
            None,
        )

        existing_marker_left = getattr(
            paragraph,
            "list_marker_left",
            None,
        )

        existing_marker_right = getattr(
            paragraph,
            "list_marker_right",
            None,
        )

        existing_content_left = getattr(
            paragraph,
            "content_left",
            None,
        )
        
        existing_marker_source = getattr(
            paragraph,
            "list_marker_source",
            ListMarkerSource.UNKNOWN,
        )

        if not isinstance(
            existing_marker_source,
            ListMarkerSource,
        ):
            try:
                existing_marker_source = (
                    ListMarkerSource(
                        str(
                            existing_marker_source
                        )
                    )
                )

            except ValueError:
                existing_marker_source = (
                    ListMarkerSource.UNKNOWN
                )

        cls._reset_paragraph(
            paragraph
        )

        first_line_text = (
            cls._first_line_text(
                paragraph
            )
        )

        marker_match = (
            cls._detect_text_marker(
                first_line_text
            )
        )

        if marker_match is not None:
            (
                marker_left,
                marker_right,
                content_left,
            ) = cls._resolve_text_marker_geometry(
                paragraph=paragraph,
                marker=marker_match.marker,
            )

            cls._assign_result(
                page=page,
                paragraph=paragraph,
                marker_match=marker_match,
                marker_source=(
                    ListMarkerSource.TEXT
                ),
                marker_left=marker_left,
                marker_right=marker_right,
                content_left=content_left,
                reason=(
                    "A supported textual list marker was "
                    "detected at the beginning of the "
                    "paragraph."
                ),
            )

            return

        # ParagraphRegionAnalyzer already attaches classified
        # vector bullets. Preserve that evidence here.
        if (
            existing_type == "bullet"
            and existing_marker
            and existing_marker_left is not None
            and existing_marker_right is not None

            # VECTOR means it was confirmed previously.
            #
            # UNKNOWN supports legacy vector-bullet metadata created
            # before ListMarkerSource existed.
            #
            # TEXT must not be preserved because it may be stale data
            # from an earlier ListItemAnalyzer run.
            and existing_marker_source
            in {
                ListMarkerSource.VECTOR,
                ListMarkerSource.UNKNOWN,
            }
        ):
            marker_match = _MarkerMatch(
                marker=str(
                    existing_marker
                ),
                list_type="bullet",
                marker_kind=(
                    ListMarkerKind.BULLET
                ),
                confidence=0.90,
            )

            cls._assign_result(
                page=page,
                paragraph=paragraph,
                marker_match=marker_match,
                marker_source=(
                    ListMarkerSource.VECTOR
                ),
                marker_left=float(
                    existing_marker_left
                ),
                marker_right=float(
                    existing_marker_right
                ),
                content_left=(
                    float(
                        existing_content_left
                    )
                    if existing_content_left
                    is not None
                    else float(
                        paragraph.left
                    )
                ),
                reason=(
                    "A classified vector bullet was matched "
                    "to this paragraph."
                ),
            )

            return

        # Preserve older numbered-item metadata when the
        # source line cannot be reconstructed.
        if (
            existing_type == "number"
            and existing_marker
        
            # Preserve only legacy metadata. A previous textual
            # detection must be recalculated from the current text.
            and existing_marker_source
            == ListMarkerSource.UNKNOWN
        ):
            marker_kind = (
                cls._classify_number_marker(
                    str(existing_marker)
                )
            )

            marker_match = _MarkerMatch(
                marker=str(
                    existing_marker
                ),
                list_type="number",
                marker_kind=marker_kind,
                confidence=0.75,
            )

            cls._assign_result(
                page=page,
                paragraph=paragraph,
                marker_match=marker_match,
                marker_source=(
                    ListMarkerSource.TEXT
                ),
                marker_left=(
                    float(existing_marker_left)
                    if existing_marker_left
                    is not None
                    else None
                ),
                marker_right=(
                    float(existing_marker_right)
                    if existing_marker_right
                    is not None
                    else None
                ),
                content_left=(
                    float(existing_content_left)
                    if existing_content_left
                    is not None
                    else float(
                        paragraph.left
                    )
                ),
                reason=(
                    "Existing numbered-item metadata was "
                    "preserved."
                ),
            )

    @classmethod
    def _attach_standalone_markers(
        cls,
        page: Page,
    ) -> None:
        """
        Attach marker-only ParagraphRegions to the following
        same-line content ParagraphRegion.

        Example PDF extraction:

            Region 23: "•"
            Region 24: "Invoices sorted by date"

        becomes:

            Region 23: marker-only, suppressed from editable output
            Region 24: genuine bullet-list item
        """

        ordered_paragraphs = (
            cls._ordered_paragraphs(
                page
            )
        )

        for index, marker_paragraph in enumerate(
            ordered_paragraphs[:-1]
        ):
            if not cls._is_standalone_marker(
                marker_paragraph
            ):
                continue

            content_paragraph = (
                ordered_paragraphs[
                    index + 1
                ]
            )

            if not cls._can_attach_standalone_marker(
                marker_paragraph=(
                    marker_paragraph
                ),
                content_paragraph=(
                    content_paragraph
                ),
            ):
                continue

            marker = str(
                marker_paragraph.list_marker
                or ""
            )

            marker_kind = getattr(
                marker_paragraph,
                "list_marker_kind",
                ListMarkerKind.UNKNOWN,
            )

            if not isinstance(
                marker_kind,
                ListMarkerKind,
            ):
                try:
                    marker_kind = (
                        ListMarkerKind(
                            str(
                                marker_kind
                            )
                        )
                    )

                except ValueError:
                    marker_kind = (
                        ListMarkerKind.UNKNOWN
                    )

            marker_source = getattr(
                marker_paragraph,
                "list_marker_source",
                ListMarkerSource.UNKNOWN,
            )

            if not isinstance(
                marker_source,
                ListMarkerSource,
            ):
                try:
                    marker_source = (
                        ListMarkerSource(
                            str(
                                marker_source
                            )
                        )
                    )

                except ValueError:
                    marker_source = (
                        ListMarkerSource.UNKNOWN
                    )

            try:
                confidence = float(
                    marker_paragraph
                    .list_confidence
                )

            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.90

            marker_match = _MarkerMatch(
                marker=marker,

                list_type=str(
                    marker_paragraph.list_type
                ),

                marker_kind=marker_kind,

                confidence=max(
                    0.0,
                    min(
                        confidence,
                        1.0,
                    ),
                ),
            )

            marker_left = getattr(
                marker_paragraph,
                "list_marker_left",
                None,
            )

            if marker_left is None:
                marker_left = float(
                    marker_paragraph.left
                )

            marker_right = getattr(
                marker_paragraph,
                "list_marker_right",
                None,
            )

            if marker_right is None:
                marker_right = float(
                    marker_paragraph.right
                )

            # Remove the result that currently belongs to the
            # marker-only region.
            page.list_item_results[:] = [
                result

                for result
                in page.list_item_results

                if (
                    result.paragraph_region_number
                    != marker_paragraph
                    .region_number
                )
            ]

            # The content paragraph becomes the actual Word list
            # paragraph.
            cls._assign_result(
                page=page,

                paragraph=content_paragraph,

                marker_match=marker_match,

                marker_source=marker_source,

                marker_left=float(
                    marker_left
                ),

                marker_right=float(
                    marker_right
                ),

                content_left=float(
                    content_paragraph.left
                ),

                reason=(
                    "A detached same-line list marker was "
                    "attached to the following content "
                    "paragraph."
                ),
            )

            # Do not export the marker as an empty Word paragraph.
            cls._reset_paragraph(
                marker_paragraph
            )

            marker_paragraph.is_list_marker_only = (
                True
            )

            marker_paragraph.list_content_region_number = (
                content_paragraph.region_number
            )


    @classmethod
    def _ordered_paragraphs(
        cls,
        page: Page,
    ) -> list[Any]:
        """
        Return paragraph regions using detected reading order.
        """

        reading_order_by_number = {
            entry.paragraph_region_number: (
                int(
                    entry.order
                )
            )

            for entry in getattr(
                page,
                "reading_order_entries",
                [],
            )
            or []
        }

        return sorted(
            [
                paragraph

                for paragraph
                in page.paragraph_regions

                if str(
                    getattr(
                        paragraph,
                        "text",
                        "",
                    )
                ).strip()
            ],

            key=lambda paragraph: (
                reading_order_by_number.get(
                    int(
                        paragraph.region_number
                    ),
                    1_000_000,
                ),
                float(
                    paragraph.top
                ),
                float(
                    paragraph.left
                ),
            ),
        )


    @classmethod
    def _is_standalone_marker(
        cls,
        paragraph: Any,
    ) -> bool:
        if (
            getattr(
                paragraph,
                "list_type",
                None,
            )
            not in {
                "bullet",
                "number",
            }
        ):
            return False

        marker = str(
            getattr(
                paragraph,
                "list_marker",
                "",
            )
            or ""
        ).strip()

        text = " ".join(
            str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
            ).split()
        )

        return bool(
            marker
            and text == marker
        )


    @classmethod
    def _can_attach_standalone_marker(
        cls,
        marker_paragraph: Any,
        content_paragraph: Any,
    ) -> bool:
        """
        Confirm that the next paragraph is visually the text
        belonging to the standalone marker.
        """

        if getattr(
            content_paragraph,
            "is_list_marker_only",
            False,
        ):
            return False

        if getattr(
            content_paragraph,
            "list_type",
            None,
        ) in {
            "bullet",
            "number",
        }:
            return False

        content_text = str(
            getattr(
                content_paragraph,
                "text",
                "",
            )
        ).strip()

        if not content_text:
            return False

        # Do not join content across different known columns or
        # layout regions.
        for attribute_name in (
            "column_id",
            "layout_region_id",
        ):
            marker_value = getattr(
                marker_paragraph,
                attribute_name,
                None,
            )

            content_value = getattr(
                content_paragraph,
                attribute_name,
                None,
            )

            if (
                marker_value is not None
                and content_value is not None
                and marker_value != content_value
            ):
                return False

        marker_left = float(
            marker_paragraph.left
        )

        marker_right = float(
            getattr(
                marker_paragraph,
                "list_marker_right",
                None,
            )
            or marker_paragraph.right
        )

        content_left = float(
            content_paragraph.left
        )

        if content_left <= marker_left:
            return False

        horizontal_gap = (
            content_left
            - marker_right
        )

        if (
            horizontal_gap < -2.0
            or horizontal_gap
            > cls.STANDALONE_MARKER_MAXIMUM_GAP
        ):
            return False

        marker_top = float(
            marker_paragraph.top
        )

        marker_bottom = float(
            marker_paragraph.bottom
        )

        content_top = float(
            content_paragraph.top
        )

        content_bottom = float(
            content_paragraph.bottom
        )

        marker_height = max(
            marker_bottom - marker_top,
            1.0,
        )

        content_height = max(
            content_bottom - content_top,
            1.0,
        )

        vertical_overlap = max(
            min(
                marker_bottom,
                content_bottom,
            )
            - max(
                marker_top,
                content_top,
            ),
            0.0,
        )

        overlap_ratio = (
            vertical_overlap
            / min(
                marker_height,
                content_height,
            )
        )

        marker_center = (
            marker_top
            + marker_bottom
        ) / 2.0

        content_center = (
            content_top
            + content_bottom
        ) / 2.0

        center_offset = abs(
            marker_center
            - content_center
        )

        if (
            overlap_ratio
            < cls
            .STANDALONE_MARKER_MINIMUM_VERTICAL_OVERLAP

            and center_offset
            > cls
            .STANDALONE_MARKER_MAXIMUM_CENTER_OFFSET
        ):
            return False

        return True

    @classmethod
    def _assign_result(
        cls,
        page: Page,
        paragraph: Any,
        marker_match: _MarkerMatch,
        marker_source: ListMarkerSource,
        marker_left: float | None,
        marker_right: float | None,
        content_left: float | None,
        reason: str,
    ) -> None:
        paragraph.list_type = (
            marker_match.list_type
        )

        paragraph.list_marker = (
            marker_match.marker
        )

        paragraph.list_level = 0

        paragraph.list_marker_kind = (
            marker_match.marker_kind
        )

        paragraph.list_marker_source = (
            marker_source
        )

        paragraph.list_confidence = (
            marker_match.confidence
        )

        paragraph.list_marker_left = (
            marker_left
        )

        paragraph.list_marker_right = (
            marker_right
        )

        paragraph.content_left = (
            content_left
        )

        result = ListItemResult(
            page_number=page.number,

            paragraph_region_number=(
                paragraph.region_number
            ),

            list_type=(
                marker_match.list_type
            ),

            marker=marker_match.marker,

            marker_kind=(
                marker_match.marker_kind
            ),

            marker_source=marker_source,

            marker_left=marker_left,
            marker_right=marker_right,
            content_left=content_left,

            level=0,

            confidence=(
                marker_match.confidence
            ),
        )

        result.add_reason(
            reason
        )

        page.list_item_results.append(
            result
        )

    @classmethod
    def _detect_text_marker(
        cls,
        text: str,
    ) -> _MarkerMatch | None:
        if not text:
            return None

        bullet_match = (
            cls.BULLET_PATTERN.match(
                text
            )
        )

        if bullet_match is not None:
            return _MarkerMatch(
                marker=bullet_match.group(
                    "marker"
                ),
                list_type="bullet",
                marker_kind=(
                    ListMarkerKind.BULLET
                ),
                confidence=0.96,
            )

        number_match = (
            cls.NUMBER_PATTERN.match(
                text
            )
        )

        if number_match is None:
            return None

        marker = number_match.group(
            "marker"
        )

        return _MarkerMatch(
            marker=marker,
            list_type="number",
            marker_kind=(
                cls._classify_number_marker(
                    marker
                )
            ),
            confidence=0.90,
        )

    @classmethod
    def _classify_number_marker(
        cls,
        marker: str,
    ) -> ListMarkerKind:
        normalized = (
            marker.strip()
        )

        if (
            normalized.startswith("(")
            and normalized.endswith(")")
        ):
            normalized = normalized[
                1:-1
            ].strip()

        else:
            normalized = normalized.rstrip(
                ".)"
            ).strip()

        if cls.MULTILEVEL_DECIMAL_PATTERN.fullmatch(
            normalized
        ):
            return (
                ListMarkerKind
                .MULTILEVEL_DECIMAL
            )

        if cls.DECIMAL_PATTERN.fullmatch(
            normalized
        ):
            return (
                ListMarkerKind.DECIMAL
            )

        if cls.ROMAN_PATTERN.fullmatch(
            normalized
        ):
            if normalized.isupper():
                return (
                    ListMarkerKind
                    .UPPER_ROMAN
                )

            return (
                ListMarkerKind
                .LOWER_ROMAN
            )

        if (
            len(normalized) == 1
            and normalized.isalpha()
        ):
            if normalized.isupper():
                return (
                    ListMarkerKind
                    .UPPER_ALPHA
                )

            return (
                ListMarkerKind
                .LOWER_ALPHA
            )

        return (
            ListMarkerKind.UNKNOWN
        )

    @classmethod
    def _resolve_text_marker_geometry(
        cls,
        paragraph: Any,
        marker: str,
    ) -> tuple[
        float | None,
        float | None,
        float | None,
    ]:
        """
        Resolve marker and content geometry from the first visible
        PDF line.
    
        A list marker can be extracted in either form:
    
            span 1 = "1."
            span 2 = " Item text"
    
        or:
    
            span 1 = "1. Item text before "
            span 2 = "bold text"
    
        In the second form, span 2 is only a formatting change. It
        must not be treated as the beginning of the list content.
        """
    
        spans = cls._first_visible_spans(
            paragraph
        )
    
        if not spans:
            return (
                None,
                None,
                getattr(
                    paragraph,
                    "content_left",
                    None,
                ),
            )
    
        marker_span = spans[0]
    
        span_left = float(
            marker_span.left
        )
    
        span_right = float(
            marker_span.right
        )
    
        marker_text = str(
            marker_span.text
            or ""
        )
    
        marker_text_stripped = (
            marker_text.strip()
        )
    
        # Marker-only first span. The following visible span is the
        # actual content span.
        if (
            marker_text_stripped == marker
            and len(spans) >= 2
        ):
            return (
                span_left,
                span_right,
                float(
                    spans[1].left
                ),
            )
    
        leading_whitespace_count = (
            len(marker_text)
            - len(marker_text.lstrip())
        )
    
        text_without_leading_space = (
            marker_text.lstrip()
        )
    
        if text_without_leading_space.startswith(
            marker
        ):
            span_width = max(
                span_right - span_left,
                0.0,
            )
    
            character_count = max(
                len(marker_text),
                1,
            )
    
            average_character_width = (
                span_width
                / character_count
            )
    
            if average_character_width <= 0.0:
                average_character_width = (
                    max(
                        float(
                            getattr(
                                marker_span,
                                "font_size",
                                10.0,
                            )
                        ),
                        1.0,
                    )
                    * cls
                    .ESTIMATED_CHARACTER_WIDTH_FACTOR
                )
    
            marker_start_character = (
                leading_whitespace_count
            )
    
            marker_end_character = (
                marker_start_character
                + len(marker)
            )
    
            content_start_character = (
                marker_end_character
            )
    
            # Include separator whitespace after the marker.
            while (
                content_start_character
                < len(marker_text)
                and marker_text[
                    content_start_character
                ].isspace()
            ):
                content_start_character += 1
    
            marker_left = (
                span_left
                + average_character_width
                * marker_start_character
            )
    
            marker_right = min(
                span_left
                + average_character_width
                * marker_end_character,
                span_right,
            )
    
            # Content begins inside the same span. Later spans may
            # merely represent bold, italic, font, or color changes.
            if (
                content_start_character
                < len(marker_text)
            ):
                content_left = min(
                    span_left
                    + average_character_width
                    * content_start_character,
                    span_right,
                )
    
            # The first span contains only marker/separator text.
            elif len(spans) >= 2:
                content_left = float(
                    spans[1].left
                )
    
            else:
                content_left = (
                    marker_right
                    + max(
                        cls.MINIMUM_MARKER_CONTENT_GAP,
                        float(
                            getattr(
                                marker_span,
                                "font_size",
                                10.0,
                            )
                        )
                        * 0.30,
                    )
                )
    
            return (
                marker_left,
                marker_right,
                content_left,
            )
    
        return (
            span_left,
            span_right,
            (
                float(
                    spans[1].left
                )
                if len(spans) >= 2
                else float(
                    paragraph.left
                )
            ),
        )

    @staticmethod
    def _first_line_text(
        paragraph: Any,
    ) -> str:
        for line in getattr(
            paragraph,
            "lines",
            [],
        ) or []:
            spans = sorted(
                [
                    span
                    for span in getattr(
                        line,
                        "spans",
                        [],
                    )
                    or []
                    if str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                    ).strip()
                ],
                key=lambda span: (
                    span.left
                ),
            )

            if spans:
                return "".join(
                    str(
                        span.text
                    )
                    for span in spans
                ).strip()

        text = str(
            getattr(
                paragraph,
                "text",
                "",
            )
        )

        return text.splitlines()[
            0
        ].strip() if text else ""

    @staticmethod
    def _first_visible_spans(
        paragraph: Any,
    ) -> list:
        for line in getattr(
            paragraph,
            "lines",
            [],
        ) or []:
            spans = sorted(
                [
                    span
                    for span in getattr(
                        line,
                        "spans",
                        [],
                    )
                    or []
                    if str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                    ).strip()
                ],
                key=lambda span: (
                    span.left
                ),
            )

            if spans:
                return spans

        return []

    @staticmethod
    def _reset_paragraph(
        paragraph: Any,
    ) -> None:
        paragraph.list_type = None
        paragraph.list_marker = None
        paragraph.list_level = 0

        paragraph.list_marker_kind = (
            ListMarkerKind.UNKNOWN
        )

        paragraph.list_marker_source = (
            ListMarkerSource.UNKNOWN
        )

        paragraph.list_confidence = 0.0

        paragraph.content_left = None
        paragraph.list_marker_left = None
        paragraph.list_marker_right = None
        
        paragraph.is_list_marker_only = False
        paragraph.list_content_region_number = None