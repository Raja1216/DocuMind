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

        marker_left = float(
            marker_span.left
        )

        marker_text = str(
            marker_span.text
        )

        marker_text_stripped = (
            marker_text.strip()
        )

        if (
            marker_text_stripped
            == marker
            and len(spans) >= 2
        ):
            return (
                marker_left,
                float(
                    marker_span.right
                ),
                float(
                    spans[1].left
                ),
            )

        if marker_text.lstrip().startswith(
            marker
        ):
            span_width = max(
                float(
                    marker_span.right
                )
                - float(
                    marker_span.left
                ),
                0.0,
            )

            visible_character_count = max(
                len(
                    marker_text.strip()
                ),
                1,
            )

            average_character_width = (
                span_width
                / visible_character_count
            )

            if average_character_width <= 0.0:
                average_character_width = (
                    max(
                        float(
                            marker_span.font_size
                        ),
                        1.0,
                    )
                    * cls
                    .ESTIMATED_CHARACTER_WIDTH_FACTOR
                )

            estimated_marker_width = (
                average_character_width
                * len(marker)
            )

            marker_right = (
                marker_left
                + estimated_marker_width
            )

            content_left = (
                float(
                    spans[1].left
                )
                if len(spans) >= 2
                else marker_right
                + max(
                    cls.MINIMUM_MARKER_CONTENT_GAP,
                    float(
                        marker_span.font_size
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
            marker_left,
            float(
                marker_span.right
            ),
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