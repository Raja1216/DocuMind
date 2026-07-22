from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any

from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableCellHorizontalAlignment,
    EditableCellVerticalAlignment,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableCellPadding,
    clamp_confidence,
)


@dataclass(slots=True)
class _CellContentGeometry:
    """Visible source-text geometry inside one editable table cell."""

    spans: list[Any] = field(
        default_factory=list
    )

    line_boxes: list[
        tuple[float, float, float, float]
    ] = field(
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
    def median_font_size(self) -> float:
        values = [
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
            float(median(values))
            if values
            else 10.0,
            1.0,
        )


class EditableTableStyleAnalyzer:
    """
    Reconstruct Word-compatible table-cell styling.

    This analyzer runs after cell content assignment and merged-cell
    detection. It resolves:

    - horizontal and vertical cell alignment;
    - conservative cell padding;
    - leading header rows;
    - individual border edges from page vector graphics;
    - preservation of existing cell fills and fallback borders.

    The analyzer never changes table structure or cell spans.
    """

    SPAN_MINIMUM_COVERAGE = 0.55
    CELL_TOLERANCE = 1.5

    ALIGNMENT_MINIMUM_TOLERANCE = 2.5
    ALIGNMENT_FONT_FACTOR = 0.35
    EDGE_ALIGNMENT_MAXIMUM_RATIO = 0.20

    JUSTIFY_EDGE_TOLERANCE = 3.5
    JUSTIFY_MINIMUM_LINES = 2

    MINIMUM_PADDING = 0.5
    MAXIMUM_PADDING = 12.0
    DEFAULT_HORIZONTAL_PADDING = 3.0
    DEFAULT_VERTICAL_PADDING = 2.0

    BORDER_EDGE_TOLERANCE = 2.5
    BORDER_MAXIMUM_THICKNESS = 3.5
    BORDER_MINIMUM_OVERLAP_RATIO = 0.45

    HEADER_MINIMUM_SCORE = 0.55
    HEADER_MINIMUM_TEXT_COVERAGE = 0.50
    HEADER_BOLD_ADVANTAGE = 0.25
    HEADER_CELL_BOLD_COVERAGE = 0.75
    HEADER_FILL_ADVANTAGE = 0.25
    HEADER_FONT_ADVANTAGE = 0.50

    STYLE_CONFIDENCE = 0.90
    PARTIAL_STYLE_CONFIDENCE = 0.72

    @classmethod
    def analyze_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.analyze_page(
                page
            )

    @classmethod
    def analyze_page(
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
            cls.analyze_table(
                page=page,
                table=table,
            )

        return tables

    @classmethod
    def analyze_table(
        cls,
        *,
        page,
        table: EditableTable,
    ) -> EditableTable:
        geometries: dict[
            int,
            _CellContentGeometry | None,
        ] = {}

        for cell in table.cells:
            geometry = cls._collect_content_geometry(
                page=page,
                cell=cell,
            )

            geometries[id(cell)] = geometry

            if geometry is None:
                continue

            cell.horizontal_alignment = (
                cls._resolve_horizontal_alignment(
                    cell=cell,
                    geometry=geometry,
                )
            )

            cell.vertical_alignment = (
                cls._resolve_vertical_alignment(
                    cell=cell,
                    geometry=geometry,
                )
            )

        horizontal_baseline, vertical_baseline = (
            cls._resolve_table_padding_baselines(
                table=table,
                geometries=geometries,
            )
        )

        for cell in table.cells:
            geometry = geometries.get(
                id(cell)
            )

            cell.padding = cls._resolve_cell_padding(
                cell=cell,
                geometry=geometry,
                horizontal_baseline=(
                    horizontal_baseline
                ),
                vertical_baseline=(
                    vertical_baseline
                ),
            )

            cell.borders = cls._resolve_cell_borders(
                page=page,
                cell=cell,
                fallback=cell.borders,
            )

            style_confidence = (
                cls.STYLE_CONFIDENCE
                if geometry is not None
                else cls.PARTIAL_STYLE_CONFIDENCE
            )

            cell.confidence = clamp_confidence(
                0.85 * float(cell.confidence)
                + 0.15 * style_confidence
            )

        cls._resolve_header_rows(
            table=table
        )

        return table

    # ---------------------------------------------------------
    # Text geometry
    # ---------------------------------------------------------

    @classmethod
    def _collect_content_geometry(
        cls,
        *,
        page,
        cell: EditableTableCell,
    ) -> _CellContentGeometry | None:
        collected_spans: list[Any] = []
        line_boxes: list[
            tuple[float, float, float, float]
        ] = []

        for block in getattr(
            page,
            "blocks",
            [],
        ) or []:
            for line in getattr(
                block,
                "lines",
                [],
            ) or []:
                line_spans: list[Any] = []

                for span in getattr(
                    line,
                    "spans",
                    [],
                ) or []:
                    if not str(
                        getattr(
                            span,
                            "text",
                            "",
                        )
                        or ""
                    ).strip():
                        continue

                    if not cls._span_belongs_to_cell(
                        span=span,
                        cell=cell,
                    ):
                        continue

                    line_spans.append(
                        span
                    )
                    collected_spans.append(
                        span
                    )

                if line_spans:
                    line_boxes.append(
                        (
                            min(
                                float(span.left)
                                for span in line_spans
                            ),
                            min(
                                float(span.top)
                                for span in line_spans
                            ),
                            max(
                                float(span.right)
                                for span in line_spans
                            ),
                            max(
                                float(span.bottom)
                                for span in line_spans
                            ),
                        )
                    )

        if not collected_spans:
            return None

        return _CellContentGeometry(
            spans=collected_spans,
            line_boxes=line_boxes,
        )

    @classmethod
    def _span_belongs_to_cell(
        cls,
        *,
        span,
        cell: EditableTableCell,
    ) -> bool:
        span_left = float(span.left)
        span_top = float(span.top)
        span_right = float(span.right)
        span_bottom = float(span.bottom)

        intersection_width = max(
            min(
                span_right,
                float(cell.bbox.right),
            )
            - max(
                span_left,
                float(cell.bbox.left),
            ),
            0.0,
        )

        intersection_height = max(
            min(
                span_bottom,
                float(cell.bbox.bottom),
            )
            - max(
                span_top,
                float(cell.bbox.top),
            ),
            0.0,
        )

        span_area = max(
            (span_right - span_left)
            * (span_bottom - span_top),
            1.0,
        )

        coverage = (
            intersection_width
            * intersection_height
            / span_area
        )

        if coverage >= cls.SPAN_MINIMUM_COVERAGE:
            return True

        center_x = (
            span_left + span_right
        ) / 2.0

        center_y = (
            span_top + span_bottom
        ) / 2.0

        tolerance = cls.CELL_TOLERANCE

        return (
            float(cell.bbox.left) - tolerance
            <= center_x
            <= float(cell.bbox.right) + tolerance
            and float(cell.bbox.top) - tolerance
            <= center_y
            <= float(cell.bbox.bottom) + tolerance
        )

    # ---------------------------------------------------------
    # Alignment
    # ---------------------------------------------------------

    @classmethod
    def _resolve_horizontal_alignment(
        cls,
        *,
        cell: EditableTableCell,
        geometry: _CellContentGeometry,
    ) -> EditableCellHorizontalAlignment:
        left_gap = max(
            geometry.left
            - float(cell.bbox.left),
            0.0,
        )

        right_gap = max(
            float(cell.bbox.right)
            - geometry.right,
            0.0,
        )

        tolerance = max(
            cls.ALIGNMENT_MINIMUM_TOLERANCE,
            geometry.median_font_size
            * cls.ALIGNMENT_FONT_FACTOR,
        )

        if cls._looks_justified(
            cell=cell,
            geometry=geometry,
        ):
            return (
                EditableCellHorizontalAlignment
                .JUSTIFY
            )

        if (
            abs(left_gap - right_gap)
            <= tolerance
            and min(
                left_gap,
                right_gap,
            )
            >= cls.MINIMUM_PADDING
        ):
            return (
                EditableCellHorizontalAlignment
                .CENTER
            )

        maximum_edge_gap = max(
            6.0,
            float(cell.width)
            * cls.EDGE_ALIGNMENT_MAXIMUM_RATIO,
        )

        if (
            right_gap + tolerance
            < left_gap
            and right_gap
            <= maximum_edge_gap
        ):
            return (
                EditableCellHorizontalAlignment
                .RIGHT
            )

        return (
            EditableCellHorizontalAlignment.LEFT
        )

    @classmethod
    def _looks_justified(
        cls,
        *,
        cell: EditableTableCell,
        geometry: _CellContentGeometry,
    ) -> bool:
        if (
            len(geometry.line_boxes)
            < cls.JUSTIFY_MINIMUM_LINES
        ):
            return False

        # The final line of a justified paragraph is normally short.
        candidate_lines = (
            geometry.line_boxes[:-1]
        )

        if not candidate_lines:
            return False

        return all(
            abs(
                line_left
                - float(cell.bbox.left)
            )
            <= cls.JUSTIFY_EDGE_TOLERANCE
            and abs(
                float(cell.bbox.right)
                - line_right
            )
            <= cls.JUSTIFY_EDGE_TOLERANCE
            for (
                line_left,
                _line_top,
                line_right,
                _line_bottom,
            ) in candidate_lines
        )

    @classmethod
    def _resolve_vertical_alignment(
        cls,
        *,
        cell: EditableTableCell,
        geometry: _CellContentGeometry,
    ) -> EditableCellVerticalAlignment:
        top_gap = max(
            geometry.top
            - float(cell.bbox.top),
            0.0,
        )

        bottom_gap = max(
            float(cell.bbox.bottom)
            - geometry.bottom,
            0.0,
        )

        tolerance = max(
            cls.ALIGNMENT_MINIMUM_TOLERANCE,
            geometry.median_font_size
            * cls.ALIGNMENT_FONT_FACTOR,
        )

        if (
            abs(top_gap - bottom_gap)
            <= tolerance
        ):
            return (
                EditableCellVerticalAlignment
                .CENTER
            )

        maximum_edge_gap = max(
            6.0,
            float(cell.height)
            * cls.EDGE_ALIGNMENT_MAXIMUM_RATIO,
        )

        if (
            bottom_gap + tolerance
            < top_gap
            and bottom_gap
            <= maximum_edge_gap
        ):
            return (
                EditableCellVerticalAlignment
                .BOTTOM
            )

        return (
            EditableCellVerticalAlignment.TOP
        )

    # ---------------------------------------------------------
    # Padding
    # ---------------------------------------------------------

    @classmethod
    def _resolve_table_padding_baselines(
        cls,
        *,
        table: EditableTable,
        geometries: dict[
            int,
            _CellContentGeometry | None,
        ],
    ) -> tuple[float, float]:
        horizontal_candidates: list[float] = []
        vertical_candidates: list[float] = []

        for cell in table.cells:
            geometry = geometries.get(
                id(cell)
            )

            if geometry is None:
                continue

            left_gap = max(
                geometry.left
                - float(cell.bbox.left),
                0.0,
            )

            right_gap = max(
                float(cell.bbox.right)
                - geometry.right,
                0.0,
            )

            top_gap = max(
                geometry.top
                - float(cell.bbox.top),
                0.0,
            )

            bottom_gap = max(
                float(cell.bbox.bottom)
                - geometry.bottom,
                0.0,
            )

            horizontal_candidates.append(
                min(
                    left_gap,
                    right_gap,
                )
            )

            vertical_candidates.append(
                min(
                    top_gap,
                    bottom_gap,
                )
            )

        horizontal_baseline = (
            float(
                median(
                    horizontal_candidates
                )
            )
            if horizontal_candidates
            else cls.DEFAULT_HORIZONTAL_PADDING
        )

        vertical_baseline = (
            float(
                median(
                    vertical_candidates
                )
            )
            if vertical_candidates
            else cls.DEFAULT_VERTICAL_PADDING
        )

        return (
            cls._clamp_padding(
                horizontal_baseline
            ),
            cls._clamp_padding(
                vertical_baseline
            ),
        )

    @classmethod
    def _resolve_cell_padding(
        cls,
        *,
        cell: EditableTableCell,
        geometry: _CellContentGeometry | None,
        horizontal_baseline: float,
        vertical_baseline: float,
    ) -> EditableTableCellPadding:
        if geometry is None:
            return EditableTableCellPadding(
                top=vertical_baseline,
                right=horizontal_baseline,
                bottom=vertical_baseline,
                left=horizontal_baseline,
            )

        left_gap = max(
            geometry.left
            - float(cell.bbox.left),
            0.0,
        )

        right_gap = max(
            float(cell.bbox.right)
            - geometry.right,
            0.0,
        )

        top_gap = max(
            geometry.top
            - float(cell.bbox.top),
            0.0,
        )

        bottom_gap = max(
            float(cell.bbox.bottom)
            - geometry.bottom,
            0.0,
        )

        left_padding = horizontal_baseline
        right_padding = horizontal_baseline
        top_padding = vertical_baseline
        bottom_padding = vertical_baseline

        if (
            cell.horizontal_alignment
            in {
                EditableCellHorizontalAlignment.LEFT,
                EditableCellHorizontalAlignment.JUSTIFY,
            }
        ):
            left_padding = cls._clamp_padding(
                left_gap
            )

        elif (
            cell.horizontal_alignment
            == EditableCellHorizontalAlignment.RIGHT
        ):
            right_padding = cls._clamp_padding(
                right_gap
            )

        elif (
            cell.horizontal_alignment
            == EditableCellHorizontalAlignment.CENTER
        ):
            centered_padding = cls._clamp_padding(
                min(
                    left_gap,
                    right_gap,
                )
            )

            left_padding = centered_padding
            right_padding = centered_padding

        if (
            cell.vertical_alignment
            == EditableCellVerticalAlignment.TOP
        ):
            top_padding = cls._clamp_padding(
                top_gap
            )

        elif (
            cell.vertical_alignment
            == EditableCellVerticalAlignment.BOTTOM
        ):
            bottom_padding = cls._clamp_padding(
                bottom_gap
            )

        elif (
            cell.vertical_alignment
            == EditableCellVerticalAlignment.CENTER
        ):
            centered_padding = cls._clamp_padding(
                min(
                    top_gap,
                    bottom_gap,
                )
            )

            top_padding = centered_padding
            bottom_padding = centered_padding

        return EditableTableCellPadding(
            top=top_padding,
            right=right_padding,
            bottom=bottom_padding,
            left=left_padding,
        )

    @classmethod
    def _clamp_padding(
        cls,
        value: float,
    ) -> float:
        return min(
            max(
                float(value),
                cls.MINIMUM_PADDING,
            ),
            cls.MAXIMUM_PADDING,
        )

    # ---------------------------------------------------------
    # Borders
    # ---------------------------------------------------------

    @classmethod
    def _resolve_cell_borders(
        cls,
        *,
        page,
        cell: EditableTableCell,
        fallback: EditableTableCellBorders,
    ) -> EditableTableCellBorders:
        detected: dict[
            str,
            list[EditableTableBorder],
        ] = {
            "top": [],
            "right": [],
            "bottom": [],
            "left": [],
        }

        for graphic in getattr(
            page,
            "vector_graphics",
            [],
        ) or []:
            cls._collect_graphic_border_candidates(
                graphic=graphic,
                cell=cell,
                detected=detected,
            )

        return EditableTableCellBorders(
            top=cls._select_border(
                detected["top"],
                fallback.top,
            ),
            right=cls._select_border(
                detected["right"],
                fallback.right,
            ),
            bottom=cls._select_border(
                detected["bottom"],
                fallback.bottom,
            ),
            left=cls._select_border(
                detected["left"],
                fallback.left,
            ),
        )

    @classmethod
    def _collect_graphic_border_candidates(
        cls,
        *,
        graphic,
        cell: EditableTableCell,
        detected: dict[
            str,
            list[EditableTableBorder],
        ],
    ) -> None:
        left = float(
            getattr(
                graphic,
                "left",
                0.0,
            )
        )
        top = float(
            getattr(
                graphic,
                "top",
                0.0,
            )
        )
        right = float(
            getattr(
                graphic,
                "right",
                left,
            )
        )
        bottom = float(
            getattr(
                graphic,
                "bottom",
                top,
            )
        )

        graphic_width = max(
            right - left,
            0.0,
        )
        graphic_height = max(
            bottom - top,
            0.0,
        )

        border = cls._border_from_graphic(
            graphic=graphic,
            graphic_width=graphic_width,
            graphic_height=graphic_height,
        )

        if border is None:
            return

        cell_left = float(cell.bbox.left)
        cell_top = float(cell.bbox.top)
        cell_right = float(cell.bbox.right)
        cell_bottom = float(cell.bbox.bottom)

        tolerance = cls.BORDER_EDGE_TOLERANCE

        # A stroked rectangle closely matching the cell rectangle
        # supplies all four edges.
        if (
            str(
                getattr(
                    graphic,
                    "drawing_type",
                    "",
                )
            ).casefold()
            == "rectangle"
            and abs(left - cell_left)
            <= tolerance
            and abs(top - cell_top)
            <= tolerance
            and abs(right - cell_right)
            <= tolerance
            and abs(bottom - cell_bottom)
            <= tolerance
        ):
            for edge_name in detected:
                detected[edge_name].append(
                    border
                )
            return

        horizontal_line = (
            graphic_height
            <= cls.BORDER_MAXIMUM_THICKNESS
            or graphic_height
            <= float(
                getattr(
                    graphic,
                    "stroke_width",
                    0.0,
                )
            )
            + tolerance
        )

        vertical_line = (
            graphic_width
            <= cls.BORDER_MAXIMUM_THICKNESS
            or graphic_width
            <= float(
                getattr(
                    graphic,
                    "stroke_width",
                    0.0,
                )
            )
            + tolerance
        )

        horizontal_overlap = max(
            min(right, cell_right)
            - max(left, cell_left),
            0.0,
        )

        vertical_overlap = max(
            min(bottom, cell_bottom)
            - max(top, cell_top),
            0.0,
        )

        horizontal_overlap_ratio = (
            horizontal_overlap
            / max(
                float(cell.width),
                1.0,
            )
        )

        vertical_overlap_ratio = (
            vertical_overlap
            / max(
                float(cell.height),
                1.0,
            )
        )

        center_y = (
            top + bottom
        ) / 2.0
        center_x = (
            left + right
        ) / 2.0

        if (
            horizontal_line
            and horizontal_overlap_ratio
            >= cls.BORDER_MINIMUM_OVERLAP_RATIO
        ):
            if abs(center_y - cell_top) <= tolerance:
                detected["top"].append(
                    border
                )

            if abs(center_y - cell_bottom) <= tolerance:
                detected["bottom"].append(
                    border
                )

        if (
            vertical_line
            and vertical_overlap_ratio
            >= cls.BORDER_MINIMUM_OVERLAP_RATIO
        ):
            if abs(center_x - cell_left) <= tolerance:
                detected["left"].append(
                    border
                )

            if abs(center_x - cell_right) <= tolerance:
                detected["right"].append(
                    border
                )

    @classmethod
    def _border_from_graphic(
        cls,
        *,
        graphic,
        graphic_width: float,
        graphic_height: float,
    ) -> EditableTableBorder | None:
        stroke_width = max(
            float(
                getattr(
                    graphic,
                    "stroke_width",
                    0.0,
                )
                or 0.0
            ),
            0.0,
        )

        stroke_color = getattr(
            graphic,
            "stroke_color",
            None,
        )

        fill_color = getattr(
            graphic,
            "fill_color",
            None,
        )

        if stroke_width > 0.0:
            width = min(
                stroke_width,
                cls.BORDER_MAXIMUM_THICKNESS,
            )
            color = stroke_color or "000000"

        else:
            shorter_side = min(
                graphic_width,
                graphic_height,
            )

            if (
                fill_color is None
                or shorter_side
                > cls.BORDER_MAXIMUM_THICKNESS
            ):
                return None

            width = max(
                shorter_side,
                0.1,
            )
            color = fill_color

        dash_pattern = str(
            getattr(
                graphic,
                "dash_pattern",
                "",
            )
            or ""
        ).casefold()

        if "dot" in dash_pattern:
            style = (
                EditableBorderLineStyle.DOTTED
            )
        elif dash_pattern not in {
            "",
            "[] 0",
            "none",
        }:
            style = (
                EditableBorderLineStyle.DASHED
            )
        else:
            style = (
                EditableBorderLineStyle.SINGLE
            )

        return EditableTableBorder(
            style=style,
            color=str(color),
            width=width,
            confidence=0.92,
        )

    @staticmethod
    def _select_border(
        candidates: list[EditableTableBorder],
        fallback: EditableTableBorder,
    ) -> EditableTableBorder:
        if not candidates:
            return EditableTableBorder(
                style=fallback.style,
                color=fallback.color,
                width=fallback.width,
                confidence=fallback.confidence,
            )

        selected = max(
            candidates,
            key=lambda border: (
                border.confidence,
                border.width,
            ),
        )

        return EditableTableBorder(
            style=selected.style,
            color=selected.color,
            width=selected.width,
            confidence=selected.confidence,
        )

    # ---------------------------------------------------------
    # Header rows
    # ---------------------------------------------------------

    @classmethod
    def _resolve_header_rows(
        cls,
        *,
        table: EditableTable,
    ) -> None:
        if not table.rows:
            return

        # Explicit header metadata from the extraction layer is
        # authoritative and must not be cleared.
        if any(
            row.is_header
            for row in table.rows
        ):
            return

        first_row = min(
            table.rows,
            key=lambda row: row.row_index,
        )

        first_cells = [
            cell
            for cell in table.cells
            if cell.row_index
            == first_row.row_index
        ]

        body_cells = [
            cell
            for cell in table.cells
            if cell.row_index
            > first_row.row_index
        ]

        if not first_cells or not body_cells:
            return

        first_text_coverage = (
            sum(
                1
                for cell in first_cells
                if cls._cell_has_text(
                    cell
                )
            )
            / len(first_cells)
        )

        if (
            first_text_coverage
            < cls.HEADER_MINIMUM_TEXT_COVERAGE
        ):
            return

        first_bold_ratio = cls._bold_ratio(
            first_cells
        )
        body_bold_ratio = cls._bold_ratio(
            body_cells
        )

        first_bold_cell_coverage = (
            cls._bold_cell_coverage(
                first_cells
            )
        )

        body_bold_cell_coverage = (
            cls._bold_cell_coverage(
                body_cells
            )
        )

        first_fill_ratio = cls._fill_ratio(
            first_cells
        )
        body_fill_ratio = cls._fill_ratio(
            body_cells
        )

        first_font_size = cls._median_font_size(
            first_cells
        )
        body_font_size = cls._median_font_size(
            body_cells
        )

        score = 0.10

        if (
            first_bold_ratio >= 0.60
            and first_bold_cell_coverage
            >= cls.HEADER_CELL_BOLD_COVERAGE
            and first_bold_ratio
            - body_bold_ratio
            >= cls.HEADER_BOLD_ADVANTAGE
            and first_bold_cell_coverage
            - body_bold_cell_coverage
            >= cls.HEADER_BOLD_ADVANTAGE
        ):
            score += 0.45

        if (
            first_fill_ratio >= 0.50
            and first_fill_ratio
            - body_fill_ratio
            >= cls.HEADER_FILL_ADVANTAGE
        ):
            score += 0.45

        if (
            first_font_size > 0.0
            and body_font_size > 0.0
            and first_font_size
            - body_font_size
            >= cls.HEADER_FONT_ADVANTAGE
        ):
            score += 0.15

        if first_text_coverage >= 0.90:
            score += 0.10

        if score >= cls.HEADER_MINIMUM_SCORE:
            first_row.is_header = True

    @staticmethod
    def _cell_has_text(
        cell: EditableTableCell,
    ) -> bool:
        return bool(
            str(
                cell.text
                or ""
            ).strip()
        )

    @classmethod
    def _bold_ratio(
        cls,
        cells: list[EditableTableCell],
    ) -> float:
        runs = [
            run
            for cell in cells
            for paragraph in (
                cell.content_paragraphs
            )
            for run in paragraph.runs
            if str(
                getattr(
                    run,
                    "text",
                    "",
                )
                or ""
            ).strip()
        ]

        if not runs:
            return 0.0

        return (
            sum(
                len(
                    str(run.text)
                )
                for run in runs
                if bool(
                    getattr(
                        run,
                        "bold",
                        False,
                    )
                )
            )
            / max(
                sum(
                    len(
                        str(run.text)
                    )
                    for run in runs
                ),
                1,
            )
        )

    @classmethod
    def _bold_cell_coverage(
        cls,
        cells: list[EditableTableCell],
    ) -> float:
        nonempty_cells = [
            cell
            for cell in cells
            if cls._cell_has_text(
                cell
            )
        ]

        if not nonempty_cells:
            return 0.0

        majority_bold_count = 0

        for cell in nonempty_cells:
            if cls._bold_ratio(
                [cell]
            ) >= 0.60:
                majority_bold_count += 1

        return (
            majority_bold_count
            / len(nonempty_cells)
        )

    @staticmethod
    def _fill_ratio(
        cells: list[EditableTableCell],
    ) -> float:
        if not cells:
            return 0.0

        return (
            sum(
                1
                for cell in cells
                if cell.fill_color
            )
            / len(cells)
        )

    @staticmethod
    def _median_font_size(
        cells: list[EditableTableCell],
    ) -> float:
        sizes = [
            float(
                getattr(
                    run,
                    "font_size",
                    0.0,
                )
                or 0.0
            )
            for cell in cells
            for paragraph in (
                cell.content_paragraphs
            )
            for run in paragraph.runs
            if float(
                getattr(
                    run,
                    "font_size",
                    0.0,
                )
                or 0.0
            )
            > 0.0
        ]

        return (
            float(median(sizes))
            if sizes
            else 0.0
        )
