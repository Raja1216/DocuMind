from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from src.models.line import Line
from src.models.page import Page
from src.models.paragraph_region import ParagraphRegion


@dataclass
class _LineRecord:
    """
    Internal representation of one visual PDF line.

    A visual line may combine fragments originating from
    multiple PyMuPDF blocks.
    """

    spans: list = field(
        default_factory=list
    )

    block_numbers: set[int] = field(
        default_factory=set
    )

    @property
    def visible_spans(self) -> list:
        return [
            span
            for span in self.spans
            if span.text.strip()
        ]

    @property
    def left(self) -> float:
        spans = self.visible_spans

        if not spans:
            return 0.0

        return min(
            span.left
            for span in spans
        )

    @property
    def top(self) -> float:
        spans = self.visible_spans

        if not spans:
            return 0.0

        return min(
            span.top
            for span in spans
        )

    @property
    def right(self) -> float:
        spans = self.visible_spans

        if not spans:
            return 0.0

        return max(
            span.right
            for span in spans
        )

    @property
    def bottom(self) -> float:
        spans = self.visible_spans

        if not spans:
            return 0.0

        return max(
            span.bottom
            for span in spans
        )

    @property
    def width(self) -> float:
        return max(
            self.right - self.left,
            0.0,
        )

    @property
    def height(self) -> float:
        return max(
            self.bottom - self.top,
            0.0,
        )

    @property
    def center_y(self) -> float:
        return (
            self.top + self.bottom
        ) / 2

    @property
    def text(self) -> str:
        return "".join(
            span.text
            for span in sorted(
                self.spans,
                key=lambda item: item.left,
            )
        )

    @property
    def font_size(self) -> float:
        sizes = [
            span.font_size
            for span in self.visible_spans
        ]

        if not sizes:
            return 0.0

        return float(
            median(sizes)
        )


class ParagraphRegionAnalyzer:
    """
    Builds page-level logical paragraphs.

    Unlike ParagraphAnalyzer, this analyzer can join wrapped
    lines that PyMuPDF placed in different text blocks.
    """

    SAME_LINE_CENTER_TOLERANCE = 3.0
    SAME_LINE_MINIMUM_OVERLAP = 0.60
    SAME_LINE_MAXIMUM_GAP = 24.0

    FONT_SIZE_TOLERANCE = 0.75

    CONTINUATION_LEFT_TOLERANCE = 8.0

    MINIMUM_LINE_ADVANCE = 2.0
    MAXIMUM_LINE_ADVANCE_FACTOR = 1.80

    CHART_HORIZONTAL_MARGIN = 45.0
    CHART_TOP_MARGIN = 30.0
    CHART_BOTTOM_MARGIN = 45.0

    FIGURE_CAPTION_PATTERN = re.compile(
        r"^\(\s*Figure\b",
        re.IGNORECASE,
    )

    TEXTUAL_LIST_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<marker>
            [•◦▪▫●○■□‣⁃⁌⁍➢➤➔✓✔]
            |
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
        (?P<separator>\s+|$)
        """,
        flags=re.VERBOSE,
    )

    TERMINAL_PARAGRAPH_CHARACTERS = (
        ".",
        "!",
        "?",
        ";",
        ":",
    )
    
    VECTOR_BULLET_MAXIMUM_GAP = 36.0
    VECTOR_BULLET_MINIMUM_GAP = -3.0

    VECTOR_BULLET_MINIMUM_VERTICAL_TOLERANCE = 5.0
    VECTOR_BULLET_VERTICAL_TOLERANCE_FACTOR = 0.75

    @classmethod
    def analyze_page(
        cls,
        page: Page,
    ) -> None:
        """
        Rebuild all logical paragraph regions on one page.
        """

        page.paragraph_regions.clear()

        line_records = cls._collect_line_records(
            page
        )

        if not line_records:
            return

        visual_lines = cls._merge_same_row_fragments(
            line_records
        )

        paragraph_groups = cls._group_visual_lines(
            visual_lines
        )

        for region_number, group in enumerate(
            paragraph_groups,
            start=1,
        ):
            page.paragraph_regions.append(
                cls._build_region(
                    page=page,
                    records=group,
                    region_number=region_number,
                )
            )
        cls._attach_vector_bullets(
            page
        ) 
        
    @classmethod
    def _attach_vector_bullets(
        cls,
        page: Page,
    ) -> None:
        """
        Match classified vector bullet shapes with the paragraph
        beginning immediately to their right.
        """
    
        bullets = [
            graphic
            for graphic in page.vector_graphics
            if graphic.category == "bullet"
        ]
    
        if not bullets:
            return
    
        used_bullet_ids: set[int] = set()
    
        for region in page.paragraph_regions:
            # Textual numbers such as "1." have already been
            # detected and should not become bullets.
            if region.list_type is not None:
                continue
            
            first_line_bounds = (
                cls._first_visible_line_bounds(
                    region
                )
            )
    
            if first_line_bounds is None:
                continue
            
            (
                line_left,
                line_top,
                _,
                line_bottom,
            ) = first_line_bounds
    
            line_center_y = (
                line_top + line_bottom
            ) / 2
    
            line_height = max(
                line_bottom - line_top,
                1.0,
            )
    
            vertical_tolerance = max(
                cls.VECTOR_BULLET_MINIMUM_VERTICAL_TOLERANCE,
                (
                    line_height
                    * cls.VECTOR_BULLET_VERTICAL_TOLERANCE_FACTOR
                ),
            )
    
            best_bullet = None
            best_score = None
    
            for bullet in bullets:
                if id(bullet) in used_bullet_ids:
                    continue
                
                bullet_center_y = (
                    bullet.top + bullet.bottom
                ) / 2
    
                vertical_difference = abs(
                    bullet_center_y - line_center_y
                )
    
                if (
                    vertical_difference
                    > vertical_tolerance
                ):
                    continue
                
                horizontal_gap = (
                    line_left - bullet.right
                )
    
                if (
                    horizontal_gap
                    < cls.VECTOR_BULLET_MINIMUM_GAP
                    or horizontal_gap
                    > cls.VECTOR_BULLET_MAXIMUM_GAP
                ):
                    continue
                
                score = (
                    vertical_difference
                    + max(
                        horizontal_gap,
                        0.0,
                    ) * 0.10
                )
    
                if (
                    best_score is None
                    or score < best_score
                ):
                    best_score = score
                    best_bullet = bullet
    
            if best_bullet is None:
                continue
            
            region.list_type = "bullet"
            region.list_marker = "•"
            region.list_level = 0
    
            region.content_left = line_left
    
            region.list_marker_left = (
                best_bullet.left
            )
    
            region.list_marker_right = (
                best_bullet.right
            )
    
            used_bullet_ids.add(
                id(best_bullet)
            )
    
    
    @staticmethod
    def _first_visible_line_bounds(
        region: ParagraphRegion,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        """
        Return the bounding rectangle of the first visible
        paragraph line.
        """
    
        for line in region.lines:
            visible_spans = [
                span
                for span in line.spans
                if span.text.strip()
            ]
    
            if not visible_spans:
                continue
            
            return (
                min(
                    span.left
                    for span in visible_spans
                ),
    
                min(
                    span.top
                    for span in visible_spans
                ),
    
                max(
                    span.right
                    for span in visible_spans
                ),
    
                max(
                    span.bottom
                    for span in visible_spans
                ),
            )
    
        return None       

    @classmethod
    def _collect_line_records(
        cls,
        page: Page,
    ) -> list[_LineRecord]:
        """
        Collect visible lines from every text block.

        Table-cell lines are excluded because they are handled
        separately by the Table Engine.
        """

        records: list[_LineRecord] = []

        for block in page.blocks:
            for line in block.lines:
                visible_spans = [
                    span
                    for span in line.spans
                    if span.text.strip()
                ]

                if not visible_spans:
                    continue

                if cls._line_is_inside_table(
                    spans=visible_spans,
                    tables=page.tables,
                ):
                    continue
                
                if cls._line_is_inside_chart(
                    spans=visible_spans,
                    vector_graphics=page.vector_graphics,
                ):
                    continue

                records.append(
                    _LineRecord(
                        spans=list(
                            line.spans
                        ),
                        block_numbers={
                            block.block_number
                        },
                    )
                )

        records.sort(
            key=lambda record: (
                record.top,
                record.left,
            )
        )

        return records

    @staticmethod
    def _line_is_inside_table(
        spans: list,
        tables: list,
    ) -> bool:
        """
        Return True when the center of a line is inside a
        detected table.
        """

        left = min(
            span.left
            for span in spans
        )

        top = min(
            span.top
            for span in spans
        )

        right = max(
            span.right
            for span in spans
        )

        bottom = max(
            span.bottom
            for span in spans
        )

        center_x = (
            left + right
        ) / 2

        center_y = (
            top + bottom
        ) / 2

        return any(
            table.left
            <= center_x
            <= table.right
            and table.top
            <= center_y
            <= table.bottom
            for table in tables
        )

    @classmethod
    def _line_is_inside_chart(
        cls,
        spans: list,
        vector_graphics: list,
    ) -> bool:
        """
        Exclude chart legends, axis values and category labels
        from normal paragraph reconstruction.
    
        Figure captions remain normal editable paragraphs.
        """
    
        chart_graphics = [
            graphic
            for graphic in vector_graphics
            if graphic.category == "chart"
        ]
    
        if not chart_graphics:
            return False
    
        visible_spans = [
            span
            for span in spans
            if span.text.strip()
        ]
    
        if not visible_spans:
            return False
    
        line_text = "".join(
            span.text
            for span in sorted(
                visible_spans,
                key=lambda item: item.left,
            )
        ).strip()
    
        # Preserve captions such as:
        # (Figure 1: Market Growth Over the Past Five Years)
        if cls.FIGURE_CAPTION_PATTERN.match(
            line_text
        ):
            return False
    
        line_left = min(
            span.left
            for span in visible_spans
        )
    
        line_top = min(
            span.top
            for span in visible_spans
        )
    
        line_right = max(
            span.right
            for span in visible_spans
        )
    
        line_bottom = max(
            span.bottom
            for span in visible_spans
        )
    
        chart_left = (
            min(
                graphic.left
                for graphic in chart_graphics
            )
            - cls.CHART_HORIZONTAL_MARGIN
        )
    
        chart_top = (
            min(
                graphic.top
                for graphic in chart_graphics
            )
            - cls.CHART_TOP_MARGIN
        )
    
        chart_right = (
            max(
                graphic.right
                for graphic in chart_graphics
            )
            + cls.CHART_HORIZONTAL_MARGIN
        )
    
        chart_bottom = (
            max(
                graphic.bottom
                for graphic in chart_graphics
            )
            + cls.CHART_BOTTOM_MARGIN
        )
    
        # Use rectangle intersection instead of only checking the
        # line center. Axis labels may partially sit outside the
        # chart's original vector bounds.
        return not (
            line_right < chart_left
            or line_left > chart_right
            or line_bottom < chart_top
            or line_top > chart_bottom
        )

    @classmethod
    def _merge_same_row_fragments(
        cls,
        records: list[_LineRecord],
    ) -> list[_LineRecord]:
        """
        Combine fragments occupying the same visual line.

        This joins a separately extracted list marker such as
        "1." with the text positioned immediately after it.
        """

        merged: list[_LineRecord] = []

        for record in records:
            best_index: int | None = None
            best_gap: float | None = None

            for index, candidate in enumerate(
                merged
            ):
                if not cls._same_visual_row(
                    candidate,
                    record,
                ):
                    continue

                horizontal_gap = cls._horizontal_gap(
                    candidate,
                    record,
                )

                if (
                    best_gap is None
                    or horizontal_gap < best_gap
                ):
                    best_gap = horizontal_gap
                    best_index = index

            if best_index is None:
                merged.append(record)
                continue

            candidate = merged[
                best_index
            ]

            candidate.spans.extend(
                record.spans
            )

            candidate.spans.sort(
                key=lambda span: span.left
            )

            candidate.block_numbers.update(
                record.block_numbers
            )

        merged.sort(
            key=lambda record: (
                record.top,
                record.left,
            )
        )

        return merged

    @classmethod
    def _same_visual_row(
        cls,
        first: _LineRecord,
        second: _LineRecord,
    ) -> bool:
        """
        Determine whether two extracted line fragments belong
        to the same visual line.
        """

        center_difference = abs(
            first.center_y
            - second.center_y
        )

        overlap = cls._vertical_overlap_ratio(
            first,
            second,
        )

        if (
            center_difference
            > cls.SAME_LINE_CENTER_TOLERANCE
            and overlap
            < cls.SAME_LINE_MINIMUM_OVERLAP
        ):
            return False

        horizontal_gap = cls._horizontal_gap(
            first,
            second,
        )

        if (
            horizontal_gap
            > cls.SAME_LINE_MAXIMUM_GAP
        ):
            return False

        if (
            abs(
                first.font_size
                - second.font_size
            )
            > cls.FONT_SIZE_TOLERANCE
        ):
            return False

        return True

    @staticmethod
    def _vertical_overlap_ratio(
        first: _LineRecord,
        second: _LineRecord,
    ) -> float:
        intersection = max(
            min(
                first.bottom,
                second.bottom,
            )
            - max(
                first.top,
                second.top,
            ),
            0.0,
        )

        smaller_height = max(
            min(
                first.height,
                second.height,
            ),
            0.01,
        )

        return (
            intersection
            / smaller_height
        )

    @staticmethod
    def _horizontal_gap(
        first: _LineRecord,
        second: _LineRecord,
    ) -> float:
        return max(
            second.left - first.right,
            first.left - second.right,
            0.0,
        )

    @classmethod
    def _group_visual_lines(
        cls,
        records: list[_LineRecord],
    ) -> list[list[_LineRecord]]:
        """
        Group visual lines into logical paragraphs.
        """

        groups: list[
            list[_LineRecord]
        ] = []

        for record in records:
            if not groups:
                groups.append(
                    [record]
                )
                continue

            current_group = groups[-1]

            if cls._is_continuation(
                group=current_group,
                current=record,
            ):
                current_group.append(
                    record
                )
            else:
                groups.append(
                    [record]
                )

        return groups

    @classmethod
    def _is_continuation(
        cls,
        group: list[_LineRecord],
        current: _LineRecord,
    ) -> bool:
        """
        Determine whether the current visual line continues the
        previous logical paragraph.

        List continuation alignment is measured against the content
        start after the marker rather than against the marker's left
        edge.
        """

        previous = group[-1]

        if (
            abs(
                previous.font_size
                - current.font_size
            )
            > cls.FONT_SIZE_TOLERANCE
        ):
            return False

        current_text = current.text.strip()

        if not current_text:
            return False

        # A textual marker starts a new list item and must never be
        # absorbed into the preceding item.
        if (
            cls._extract_textual_marker(
                current_text
            )
            is not None
        ):
            return False

        expected_left = (
            cls._group_content_left(
                group
            )
        )

        reference_font_size = max(
            float(
                previous.font_size
            ),
            float(
                current.font_size
            ),
            1.0,
        )

        left_tolerance = max(
            float(
                cls.CONTINUATION_LEFT_TOLERANCE
            ),
            reference_font_size * 0.90,
        )

        if (
            abs(
                float(
                    current.left
                )
                - float(
                    expected_left
                )
            )
            > left_tolerance
        ):
            return False

        # Use line-top advancement rather than bbox bottom/top gap.
        #
        # PDF font bounding boxes can overlap vertically even when two
        # lines are normal consecutive lines.
        line_advance = (
            float(
                current.top
            )
            - float(
                previous.top
            )
        )

        if (
            line_advance
            < cls.MINIMUM_LINE_ADVANCE
        ):
            return False

        maximum_line_advance = (
            reference_font_size
            * cls.MAXIMUM_LINE_ADVANCE_FACTOR
        )

        if (
            line_advance
            > maximum_line_advance
        ):
            return False

        same_source_block = bool(
            previous.block_numbers
            & current.block_numbers
        )

        # Consecutive lines originating from one PyMuPDF block normally
        # belong to the same logical paragraph.
        if same_source_block:
            return True

        previous_text = previous.text.rstrip()

        if not previous_text:
            return False

        # Explicit word hyphenation indicates continuation.
        if previous_text.endswith("-"):
            return True

        # Across independent PDF blocks, terminal punctuation normally
        # indicates a genuine paragraph boundary.
        if previous_text.endswith(
            cls.TERMINAL_PARAGRAPH_CHARACTERS
        ):
            return False

        return True

    @classmethod
    def _group_content_left(
        cls,
        group: list[_LineRecord],
    ) -> float:
        """
        Return the expected left edge of wrapped paragraph text.

        For a list item, the expected edge is the text position
        after the marker, not the marker's own left position.
        """

        if not group:
            return 0.0

        first_line = group[0]

        visible_spans = sorted(
            [
                span
                for span in first_line.visible_spans
                if str(
                    getattr(
                        span,
                        "text",
                        "",
                    )
                ).strip()
            ],
            key=lambda span: float(
                span.left
            ),
        )

        if not visible_spans:
            return float(
                first_line.left
            )

        first_span = visible_spans[0]

        raw_text = str(
            getattr(
                first_span,
                "text",
                "",
            )
            or ""
        )

        leading_whitespace_length = (
            len(raw_text)
            - len(raw_text.lstrip())
        )

        visible_text = raw_text.lstrip()

        marker_match = (
            cls.TEXTUAL_LIST_PATTERN.match(
                visible_text
            )
        )

        if marker_match is None:
            return float(
                first_line.left
            )

        marker = marker_match.group(
            "marker"
        )

        text_after_marker = visible_text[
            marker_match.end():
        ].strip()

        # Marker and content are in separate spans:
        #
        # span 1 = "•"
        # span 2 = "Identify the target..."
        if (
            not text_after_marker
            and len(visible_spans) >= 2
        ):
            return float(
                visible_spans[1].left
            )

        span_left = float(
            first_span.left
        )

        span_right = float(
            first_span.right
        )

        span_width = max(
            span_right - span_left,
            0.0,
        )

        visible_character_count = max(
            len(
                visible_text
            ),
            1,
        )

        average_character_width = (
            span_width
            / visible_character_count
        )

        if average_character_width <= 0.0:
            average_character_width = max(
                float(
                    getattr(
                        first_span,
                        "font_size",
                        10.0,
                    )
                )
                * 0.48,
                1.0,
            )

        # marker_match.end() includes marker punctuation and the
        # following whitespace.
        consumed_character_count = (
            leading_whitespace_length
            + marker_match.end()
        )

        estimated_content_left = (
            span_left
            + (
                average_character_width
                * consumed_character_count
            )
        )

        minimum_marker_width = max(
            float(
                getattr(
                    first_span,
                    "font_size",
                    10.0,
                )
            )
            * 0.90,
            8.0,
        )

        estimated_content_left = max(
            estimated_content_left,
            span_left + minimum_marker_width,
        )

        # Never return a coordinate beyond the first span.
        return min(
            estimated_content_left,
            span_right,
        )

    @classmethod
    def _build_region(
        cls,
        page: Page,
        records: list[_LineRecord],
        region_number: int,
    ) -> ParagraphRegion:
        lines = [
            Line(
                spans=sorted(
                    record.spans,
                    key=lambda span: span.left,
                )
            )
            for record in records
        ]

        all_spans = [
            span
            for line in lines
            for span in line.spans
            if span.text.strip()
        ]

        if not all_spans:
            raise ValueError(
                "Cannot build a paragraph region without visible spans."
            )

        first_line_text = (
            records[0]
            .text
            .strip()
        )

        list_marker = (
            cls._extract_textual_marker(
                first_line_text
            )
        )

        list_type = (
            "number"
            if list_marker is not None
            else None
        )

        content_left = (
            cls._group_content_left(
                records
            )
        )

        first_line_spans = sorted(
            records[0].visible_spans,
            key=lambda span: span.left,
        )

        marker_span = (
            first_line_spans[0]
            if list_marker is not None
            and first_line_spans
            else None
        )
        
        return ParagraphRegion(
            page_number=page.number,

            region_number=region_number,

            left=min(
                span.left
                for span in all_spans
            ),

            top=min(
                span.top
                for span in all_spans
            ),

            right=max(
                span.right
                for span in all_spans
            ),

            bottom=max(
                span.bottom
                for span in all_spans
            ),

            lines=lines,

            text="\n".join(
                record.text.strip()
                for record in records
                if record.text.strip()
            ),

            source_block_numbers=sorted({
                block_number
                for record in records
                for block_number
                in record.block_numbers
            }),

            list_type=list_type,
            list_marker=list_marker,
            list_level=0,

            content_left=content_left,
            
            list_marker_left=(
                marker_span.left
                if marker_span is not None
                else None
            ),

            list_marker_right=(
                marker_span.right
                if marker_span is not None
                else None
            ),
        )

    @classmethod
    def _extract_textual_marker(
        cls,
        text: str,
    ) -> str | None:
        match = cls.TEXTUAL_LIST_PATTERN.match(
            text
        )

        if match is None:
            return None

        return match.group(
            "marker"
        )