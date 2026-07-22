from __future__ import annotations

from dataclasses import dataclass, field
import re
from statistics import median
from typing import Any

from src.models.color.rgb_color import RGBColor
from src.models.editable_table import (
    EditableTable,
    EditableTableCell,
    EditableTableCellParagraph,
)
from src.models.geometry.rectangle import Rectangle
from src.models.text_run import TextRun


@dataclass(slots=True)
class _CellLineFragment:
    """Visible source spans belonging to one PDF line fragment."""

    block_number: int

    line_index: int

    spans: list[Any] = field(
        default_factory=list
    )

    @property
    def left(self) -> float:
        return min(
            float(span.left)
            for span in self.spans
        )

    @property
    def top(self) -> float:
        return min(
            float(span.top)
            for span in self.spans
        )

    @property
    def right(self) -> float:
        return max(
            float(span.right)
            for span in self.spans
        )

    @property
    def bottom(self) -> float:
        return max(
            float(span.bottom)
            for span in self.spans
        )

    @property
    def center_y(self) -> float:
        return (
            self.top
            + self.bottom
        ) / 2.0

    @property
    def font_size(self) -> float:
        sizes = [
            float(
                getattr(
                    span,
                    "font_size",
                    0.0,
                )
                or 0.0
            )
            for span in self.spans
        ]

        return max(
            float(median(sizes))
            if sizes
            else 0.0,
            1.0,
        )


@dataclass(slots=True)
class _VisualCellLine:
    """Same-baseline fragments merged into one visual cell line."""

    fragments: list[_CellLineFragment] = field(
        default_factory=list
    )

    @property
    def spans(self) -> list[Any]:
        return sorted(
            [
                span
                for fragment in self.fragments
                for span in fragment.spans
            ],
            key=lambda span: (
                float(span.left),
                float(span.top),
            ),
        )

    @property
    def top(self) -> float:
        return min(
            fragment.top
            for fragment in self.fragments
        )

    @property
    def bottom(self) -> float:
        return max(
            fragment.bottom
            for fragment in self.fragments
        )

    @property
    def left(self) -> float:
        return min(
            fragment.left
            for fragment in self.fragments
        )

    @property
    def center_y(self) -> float:
        return (
            self.top
            + self.bottom
        ) / 2.0

    @property
    def font_size(self) -> float:
        return max(
            float(
                median(
                    [
                        fragment.font_size
                        for fragment
                        in self.fragments
                    ]
                )
            ),
            1.0,
        )

    @property
    def source_line_references(
        self,
    ) -> list[tuple[int, int]]:
        return sorted(
            {
                (
                    fragment.block_number,
                    fragment.line_index,
                )
                for fragment in self.fragments
            }
        )


class EditableTableContentAssigner:
    """
    Assign reliable source text and formatting to editable cells.

    Extraction-side ``TableCell.text`` can lose underscores,
    spaces or formatting. This analyzer rebuilds cell content from
    the page's original text spans while retaining the extracted
    text as a safe fallback when no reliable spans are available.
    """

    SPAN_MINIMUM_COVERAGE = 0.55

    PARAGRAPH_MINIMUM_COVERAGE = 0.75

    CELL_TOLERANCE = 1.5

    SAME_BASELINE_MINIMUM_TOLERANCE = 2.5

    SAME_BASELINE_FONT_FACTOR = 0.35

    MAXIMUM_CONTINUATION_ADVANCE_FACTOR = 1.90

    INLINE_SPACE_MINIMUM_GAP = 0.50

    INLINE_SPACE_GAP_FACTOR = 0.04

    CONTENT_CONFIDENCE = 0.96

    PARTIAL_CONTENT_CONFIDENCE = 0.78

    TEXTUAL_LIST_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<marker>
            [•◦▪▫●○■□‣⁃⁌⁍➢➤➔✓✔]
            |
            \(\s*(?:\d+(?:\.\d+)*|[A-Za-z]|[ivxlcdmIVXLCDM]+)\s*\)
            |
            (?:\d+(?:\.\d+)*|[A-Za-z]|[ivxlcdmIVXLCDM]+)[\.\)]
        )
        (?P<separator>\s+|$)
        """,
        flags=re.VERBOSE,
    )

    @classmethod
    def assign_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.assign_page(page)

    @classmethod
    def assign_page(
        cls,
        page,
    ) -> list[EditableTable]:
        tables = list(
            getattr(
                page,
                "editable_tables",
                [],
            )
            or []
        )

        for table in tables:
            cls.assign_table(
                page=page,
                table=table,
            )

        return tables

    @classmethod
    def assign_table(
        cls,
        page,
        table: EditableTable,
    ) -> EditableTable:
        for cell in table.cells:
            cls._assign_cell(
                page=page,
                table=table,
                cell=cell,
            )

        return table

    @classmethod
    def _assign_cell(
        cls,
        *,
        page,
        table: EditableTable,
        cell: EditableTableCell,
    ) -> None:
        # Reanalysis must replace stale semantic content.
        cell.paragraphs.clear()
        cell.paragraph_region_numbers.clear()
        cell.content_paragraphs.clear()

        cls._attach_paragraph_regions(
            page=page,
            cell=cell,
        )

        fragments = cls._collect_line_fragments(
            page=page,
            cell=cell,
        )

        if not fragments:
            if str(cell.text or "").strip():
                cell.add_warning(
                    (
                        "No reliable page text spans were found "
                        "inside the cell; extracted table text "
                        "was retained."
                    )
                )
            return

        visual_lines = cls._merge_same_baseline_fragments(
            fragments
        )

        content_paragraphs = cls._build_content_paragraphs(
            visual_lines=visual_lines,
            paragraph_regions=(
                cell.paragraphs
            ),
        )

        if not content_paragraphs:
            return

        rebuilt_text = "\n".join(
            paragraph.text
            for paragraph in content_paragraphs
            if paragraph.text
        ).strip()

        if not rebuilt_text:
            return

        cell.content_paragraphs.extend(
            content_paragraphs
        )

        cell.text = rebuilt_text

        cell.confidence = max(
            float(cell.confidence),
            min(
                (
                    cls.CONTENT_CONFIDENCE
                    if all(
                        paragraph.confidence
                        >= cls.CONTENT_CONFIDENCE
                        for paragraph
                        in content_paragraphs
                    )
                    else cls.PARTIAL_CONTENT_CONFIDENCE
                ),
                1.0,
            ),
        )

        # A grid-created cell with reliable source text is still
        # diagnostically synthetic, but it is no longer empty.
        if cell.is_synthetic:
            cell.add_warning(
                (
                    "Synthetic grid cell received reliable "
                    "source text from page spans."
                )
            )

    # ---------------------------------------------------------
    # Paragraph-region provenance
    # ---------------------------------------------------------

    @classmethod
    def _attach_paragraph_regions(
        cls,
        *,
        page,
        cell: EditableTableCell,
    ) -> None:
        matches: list[Any] = []

        for paragraph in getattr(
            page,
            "paragraph_regions",
            [],
        ) or []:
            if not str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
                or ""
            ).strip():
                continue

            paragraph_bbox = cls._bbox_from_source(
                paragraph
            )

            if paragraph_bbox is None:
                continue

            coverage = cls._coverage_ratio(
                paragraph_bbox,
                cell.bbox,
            )

            if (
                coverage
                < cls.PARAGRAPH_MINIMUM_COVERAGE
            ):
                continue

            matches.append(paragraph)

        matches.sort(
            key=lambda paragraph: (
                float(paragraph.top),
                float(paragraph.left),
                int(
                    getattr(
                        paragraph,
                        "region_number",
                        0,
                    )
                    or 0
                ),
            )
        )

        for paragraph in matches:
            region_number = cls._safe_integer(
                getattr(
                    paragraph,
                    "region_number",
                    None,
                )
            )

            cell.paragraphs.append(paragraph)

            if (
                region_number is not None
                and region_number
                not in cell.paragraph_region_numbers
            ):
                cell.paragraph_region_numbers.append(
                    region_number
                )

    # ---------------------------------------------------------
    # Raw page-line collection
    # ---------------------------------------------------------

    @classmethod
    def _collect_line_fragments(
        cls,
        *,
        page,
        cell: EditableTableCell,
    ) -> list[_CellLineFragment]:
        fragments: list[_CellLineFragment] = []

        for block in getattr(
            page,
            "blocks",
            [],
        ) or []:
            block_number = cls._safe_integer(
                getattr(
                    block,
                    "block_number",
                    None,
                )
            )

            if block_number is None:
                block_number = len(fragments)

            for line_index, line in enumerate(
                getattr(
                    block,
                    "lines",
                    [],
                )
                or []
            ):
                matching_spans = [
                    span
                    for span in getattr(
                        line,
                        "spans",
                        [],
                    )
                    or []
                    if cls._span_belongs_to_cell(
                        span=span,
                        cell=cell,
                    )
                ]

                if not matching_spans:
                    continue

                fragments.append(
                    _CellLineFragment(
                        block_number=block_number,
                        line_index=line_index,
                        spans=sorted(
                            matching_spans,
                            key=lambda span: (
                                float(span.left),
                                float(span.top),
                            ),
                        ),
                    )
                )

        fragments.sort(
            key=lambda fragment: (
                fragment.center_y,
                fragment.left,
                fragment.block_number,
                fragment.line_index,
            )
        )

        return fragments

    @classmethod
    def _span_belongs_to_cell(
        cls,
        *,
        span,
        cell: EditableTableCell,
    ) -> bool:
        text = str(
            getattr(
                span,
                "text",
                "",
            )
            or ""
        )

        if not text.strip():
            return False

        span_bbox = cls._bbox_from_source(span)

        if span_bbox is None:
            return False

        center_x = (
            float(span_bbox.left)
            + float(span_bbox.right)
        ) / 2.0

        center_y = (
            float(span_bbox.top)
            + float(span_bbox.bottom)
        ) / 2.0

        if (
            float(cell.bbox.left)
            - cls.CELL_TOLERANCE
            <= center_x
            <= float(cell.bbox.right)
            + cls.CELL_TOLERANCE
            and float(cell.bbox.top)
            - cls.CELL_TOLERANCE
            <= center_y
            <= float(cell.bbox.bottom)
            + cls.CELL_TOLERANCE
        ):
            return True

        return (
            cls._coverage_ratio(
                span_bbox,
                cell.bbox,
            )
            >= cls.SPAN_MINIMUM_COVERAGE
        )

    # ---------------------------------------------------------
    # Visual-line and paragraph construction
    # ---------------------------------------------------------

    @classmethod
    def _merge_same_baseline_fragments(
        cls,
        fragments: list[_CellLineFragment],
    ) -> list[_VisualCellLine]:
        visual_lines: list[_VisualCellLine] = []

        for fragment in fragments:
            target: _VisualCellLine | None = None

            for candidate in reversed(
                visual_lines
            ):
                tolerance = max(
                    cls.SAME_BASELINE_MINIMUM_TOLERANCE,
                    min(
                        candidate.font_size,
                        fragment.font_size,
                    )
                    * cls.SAME_BASELINE_FONT_FACTOR,
                )

                vertical_distance = abs(
                    candidate.center_y
                    - fragment.center_y
                )

                if vertical_distance <= tolerance:
                    target = candidate
                    break

                if (
                    fragment.center_y
                    - candidate.center_y
                    > tolerance
                ):
                    break

            if target is None:
                visual_lines.append(
                    _VisualCellLine(
                        fragments=[fragment]
                    )
                )
            else:
                target.fragments.append(fragment)

        visual_lines.sort(
            key=lambda line: (
                line.center_y,
                line.left,
            )
        )

        return visual_lines

    @classmethod
    def _build_content_paragraphs(
        cls,
        *,
        visual_lines: list[_VisualCellLine],
        paragraph_regions: list[Any],
    ) -> list[EditableTableCellParagraph]:
        paragraphs: list[
            EditableTableCellParagraph
        ] = []

        previous_line: _VisualCellLine | None = None

        for visual_line in visual_lines:
            runs = cls._build_runs(
                visual_line.spans
            )

            text = "".join(
                run.text
                for run in runs
            ).strip()

            if not text:
                continue

            marker_match = (
                cls.TEXTUAL_LIST_PATTERN.match(
                    text
                )
            )

            paragraph_region = (
                cls._find_matching_paragraph_region(
                    visual_line=visual_line,
                    paragraph_regions=(
                        paragraph_regions
                    ),
                )
            )

            should_continue = (
                previous_line is not None
                and not marker_match
                and not cls._line_starts_new_paragraph(
                    previous_line=previous_line,
                    current_line=visual_line,
                    current_text=text,
                )
            )

            if should_continue and paragraphs:
                cls._append_line_to_paragraph(
                    paragraph=paragraphs[-1],
                    line_runs=runs,
                    line_reference=(
                        visual_line
                        .source_line_references
                    ),
                )

                previous_line = visual_line
                continue

            region_number = (
                cls._safe_integer(
                    getattr(
                        paragraph_region,
                        "region_number",
                        None,
                    )
                )
                if paragraph_region is not None
                else None
            )

            list_marker = (
                marker_match.group("marker")
                if marker_match is not None
                else getattr(
                    paragraph_region,
                    "list_marker",
                    None,
                )
            )

            paragraphs.append(
                EditableTableCellParagraph(
                    text=text,
                    runs=runs,
                    source_line_references=(
                        visual_line
                        .source_line_references
                    ),
                    paragraph_region_number=(
                        region_number
                    ),
                    is_list_item=bool(
                        marker_match
                        or getattr(
                            paragraph_region,
                            "list_type",
                            None,
                        )
                    ),
                    list_marker=list_marker,
                    confidence=(
                        cls.CONTENT_CONFIDENCE
                    ),
                )
            )

            previous_line = visual_line

        return paragraphs

    @classmethod
    def _line_starts_new_paragraph(
        cls,
        *,
        previous_line: _VisualCellLine,
        current_line: _VisualCellLine,
        current_text: str,
    ) -> bool:
        if cls.TEXTUAL_LIST_PATTERN.match(
            current_text
        ):
            return True

        line_advance = (
            current_line.center_y
            - previous_line.center_y
        )

        reference_font_size = max(
            previous_line.font_size,
            current_line.font_size,
            1.0,
        )

        return (
            line_advance
            > reference_font_size
            * cls.MAXIMUM_CONTINUATION_ADVANCE_FACTOR
        )

    @classmethod
    def _append_line_to_paragraph(
        cls,
        *,
        paragraph: EditableTableCellParagraph,
        line_runs: list[TextRun],
        line_reference: list[tuple[int, int]],
    ) -> None:
        if not line_runs:
            return

        if paragraph.runs:
            previous_text = paragraph.runs[-1].text
            next_text = line_runs[0].text

            if cls._needs_boundary_space(
                previous_text=previous_text,
                current_text=next_text,
            ):
                cls._append_run(
                    paragraph.runs,
                    cls._copy_run(
                        paragraph.runs[-1],
                        " ",
                    ),
                )

        for run in line_runs:
            cls._append_run(
                paragraph.runs,
                run,
            )

        paragraph.text = "".join(
            run.text
            for run in paragraph.runs
        ).strip()

        for reference in line_reference:
            if (
                reference
                not in paragraph.source_line_references
            ):
                paragraph.source_line_references.append(
                    reference
                )

        paragraph.confidence = min(
            paragraph.confidence,
            cls.PARTIAL_CONTENT_CONFIDENCE,
        )

    @classmethod
    def _find_matching_paragraph_region(
        cls,
        *,
        visual_line: _VisualCellLine,
        paragraph_regions: list[Any],
    ) -> Any | None:
        best: tuple[float, Any] | None = None

        line_bbox = Rectangle(
            left=min(
                float(span.left)
                for span in visual_line.spans
            ),
            top=min(
                float(span.top)
                for span in visual_line.spans
            ),
            right=max(
                float(span.right)
                for span in visual_line.spans
            ),
            bottom=max(
                float(span.bottom)
                for span in visual_line.spans
            ),
        )

        for paragraph in paragraph_regions:
            paragraph_bbox = cls._bbox_from_source(
                paragraph
            )

            if paragraph_bbox is None:
                continue

            coverage = cls._coverage_ratio(
                line_bbox,
                paragraph_bbox,
            )

            if best is None or coverage > best[0]:
                best = (
                    coverage,
                    paragraph,
                )

        if best is None or best[0] <= 0.0:
            return None

        return best[1]

    # ---------------------------------------------------------
    # Formatted runs
    # ---------------------------------------------------------

    @classmethod
    def _build_runs(
        cls,
        spans: list[Any],
    ) -> list[TextRun]:
        runs: list[TextRun] = []

        previous_span = None
        previous_raw_text = ""

        for span in sorted(
            spans,
            key=lambda item: (
                float(item.left),
                float(item.top),
            ),
        ):
            raw_text = cls._normalize_inline_text(
                str(
                    getattr(
                        span,
                        "text",
                        "",
                    )
                    or ""
                )
            )

            visible_text = raw_text.strip()

            if not visible_text:
                continue

            if (
                previous_span is not None
                and cls._needs_space_between_spans(
                    previous_span=previous_span,
                    current_span=span,
                    previous_raw_text=(
                        previous_raw_text
                    ),
                    current_raw_text=raw_text,
                )
            ):
                cls._append_run(
                    runs,
                    cls._text_run_from_span(
                        span=previous_span,
                        text=" ",
                    ),
                )

            cls._append_run(
                runs,
                cls._text_run_from_span(
                    span=span,
                    text=visible_text,
                ),
            )

            previous_span = span
            previous_raw_text = raw_text

        return runs

    @staticmethod
    def _normalize_inline_text(
        text: str,
    ) -> str:
        normalized = (
            text
            .replace("\u00a0", " ")
            .replace("\u2007", " ")
            .replace("\u202f", " ")
        )

        normalized = re.sub(
            r"[\t\r\n\f\v]+",
            " ",
            normalized,
        )

        return re.sub(
            r" {2,}",
            " ",
            normalized,
        )

    @classmethod
    def _needs_space_between_spans(
        cls,
        *,
        previous_span,
        current_span,
        previous_raw_text: str,
        current_raw_text: str,
    ) -> bool:
        if not previous_raw_text or not current_raw_text:
            return False

        if (
            previous_raw_text[-1:].isspace()
            or current_raw_text[:1].isspace()
        ):
            return True

        previous_visible = previous_raw_text.rstrip()
        current_visible = current_raw_text.lstrip()

        if not previous_visible or not current_visible:
            return False

        if current_visible[0] in {
            ".", ",", ";", ":", "!", "?", "%",
            ")", "]", "}",
        }:
            return False

        if previous_visible[-1] in {
            "(", "[", "{", "/", "\\", "–", "—",
        }:
            return False

        horizontal_gap = (
            float(current_span.left)
            - float(previous_span.right)
        )

        if horizontal_gap <= 0.0:
            return False

        reference_font_size = max(
            min(
                float(
                    getattr(
                        previous_span,
                        "font_size",
                        1.0,
                    )
                    or 1.0
                ),
                float(
                    getattr(
                        current_span,
                        "font_size",
                        1.0,
                    )
                    or 1.0
                ),
            ),
            1.0,
        )

        threshold = max(
            cls.INLINE_SPACE_MINIMUM_GAP,
            reference_font_size
            * cls.INLINE_SPACE_GAP_FACTOR,
        )

        return horizontal_gap >= threshold

    @staticmethod
    def _needs_boundary_space(
        *,
        previous_text: str,
        current_text: str,
    ) -> bool:
        previous = str(previous_text or "")
        current = str(current_text or "")

        if not previous or not current:
            return False

        if (
            previous[-1:].isspace()
            or current[:1].isspace()
        ):
            return False

        if current[0] in {
            ".", ",", ";", ":", "!", "?", "%",
            ")", "]", "}",
        }:
            return False

        if previous[-1] in {
            "(", "[", "{", "/", "\\", "–", "—", "-",
        }:
            return False

        return True

    @staticmethod
    def _text_run_from_span(
        *,
        span,
        text: str,
    ) -> TextRun:
        font_name = str(
            getattr(
                span,
                "font",
                "Arial",
            )
            or "Arial"
        )

        font_name_lower = font_name.casefold()

        flags = int(
            getattr(
                span,
                "flags",
                0,
            )
            or 0
        )

        return TextRun(
            text=text,
            font_name=font_name,
            font_size=max(
                float(
                    getattr(
                        span,
                        "font_size",
                        11.0,
                    )
                    or 11.0
                ),
                0.5,
            ),
            color=getattr(
                span,
                "color",
                RGBColor(0, 0, 0),
            ),
            bold=(
                bool(flags & (1 << 4))
                or "bold" in font_name_lower
                or "semibold" in font_name_lower
                or "extrabold" in font_name_lower
            ),
            italic=(
                bool(flags & (1 << 1))
                or "italic" in font_name_lower
                or "oblique" in font_name_lower
            ),
        )

    @classmethod
    def _append_run(
        cls,
        runs: list[TextRun],
        run: TextRun,
    ) -> None:
        if not run.text:
            return

        previous = runs[-1] if runs else None

        if (
            previous is not None
            and cls._runs_have_same_style(
                previous,
                run,
            )
        ):
            previous.text += run.text
            return

        runs.append(run)

    @staticmethod
    def _runs_have_same_style(
        first: TextRun,
        second: TextRun,
    ) -> bool:
        return (
            first.font_name == second.font_name
            and float(first.font_size)
            == float(second.font_size)
            and first.color == second.color
            and first.bold == second.bold
            and first.italic == second.italic
        )

    @staticmethod
    def _copy_run(
        source: TextRun,
        text: str,
    ) -> TextRun:
        return TextRun(
            text=text,
            font_name=source.font_name,
            font_size=source.font_size,
            color=source.color,
            bold=source.bold,
            italic=source.italic,
        )

    # ---------------------------------------------------------
    # Geometry helpers
    # ---------------------------------------------------------

    @staticmethod
    def _bbox_from_source(
        source,
    ) -> Rectangle | None:
        try:
            left = float(source.left)
            top = float(source.top)
            right = float(source.right)
            bottom = float(source.bottom)
        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            return None

        if right < left:
            left, right = right, left

        if bottom < top:
            top, bottom = bottom, top

        return Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )

    @staticmethod
    def _coverage_ratio(
        subject: Rectangle,
        container: Rectangle,
    ) -> float:
        width = max(
            min(
                float(subject.right),
                float(container.right),
            )
            - max(
                float(subject.left),
                float(container.left),
            ),
            0.0,
        )

        height = max(
            min(
                float(subject.bottom),
                float(container.bottom),
            )
            - max(
                float(subject.top),
                float(container.top),
            ),
            0.0,
        )

        subject_area = max(
            (
                float(subject.right)
                - float(subject.left)
            )
            * (
                float(subject.bottom)
                - float(subject.top)
            ),
            1.0,
        )

        return (
            width
            * height
        ) / subject_area

    @staticmethod
    def _safe_integer(
        value,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None
