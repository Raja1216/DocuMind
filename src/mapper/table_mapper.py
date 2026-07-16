from __future__ import annotations

from dataclasses import dataclass

from src.models.table import Table
from src.models.table_cell import TableCell
from src.models.table_border_style import TableBorderStyle

import fitz
from collections import Counter
from statistics import median


@dataclass(slots=True)
class _DetectedRow:
    """
    Internal normalized representation of one PyMuPDF
    table row.
    """

    original_index: int
    cells: list


class TableMapper:
    """
    Maps one PyMuPDF table into DocuMind table models.

    This mapper:
    - preserves row and column positions;
    - preserves None placeholders;
    - removes false full-width wrapper rows;
    - recalculates the final table bounding box.
    """

    FULL_WIDTH_THRESHOLD = 0.90
    
    DRAWING_BBOX_TOLERANCE = 2.0

    MAX_BORDER_THICKNESS = 3.0
    MIN_BORDER_THICKNESS = 0.10

    MIN_LINE_ASPECT_RATIO = 4.0

    DEFAULT_BORDER_COLOR = "#B7B7B7"
    DEFAULT_BORDER_THICKNESS = 0.5
    
    CELL_FILL_MIN_COVERAGE = 0.70
    CELL_FILL_EDGE_TOLERANCE = 1.5

    @staticmethod
    def map(
        pymupdf_table,
        pdf_page,
        page_number: int,
    ) -> Table:
        extracted_rows = (
            pymupdf_table.extract()
            or []
        )

        detected_rows = (
            TableMapper._collect_rows(
                pymupdf_table
            )
        )

        normalized_rows = (
            TableMapper._trim_wrapper_rows(
                rows=detected_rows,
                table_bbox=pymupdf_table.bbox,
            )
        )

        if not normalized_rows:
            normalized_rows = detected_rows

        table_bbox = (
            TableMapper._calculate_table_bbox(
                rows=normalized_rows,
                fallback_bbox=pymupdf_table.bbox,
            )
        )

        column_count = int(
            pymupdf_table.col_count
        )

        table = Table(
            page_number=page_number,

            left=float(table_bbox[0]),
            top=float(table_bbox[1]),
            right=float(table_bbox[2]),
            bottom=float(table_bbox[3]),

            row_count=len(normalized_rows),
            column_count=column_count,
        )
        
        table.border_style = (
            TableMapper._detect_border_style(
                pdf_page=pdf_page,
                table_bbox=table_bbox,
            )
        )

        TableMapper._map_cells(
            table=table,
            rows=normalized_rows,
            extracted_rows=extracted_rows,
            pdf_page=pdf_page,
            page_number=page_number,
        )

        return table

    @staticmethod
    def _collect_rows(
        pymupdf_table,
    ) -> list[_DetectedRow]:
        """
        Read cell rectangles from PyMuPDF's row objects.

        Unlike pymupdf_table.cells, row.cells preserves
        None placeholders for merged or missing cells.
        """

        rows: list[_DetectedRow] = []

        for row_index, row in enumerate(
            pymupdf_table.rows
        ):
            rows.append(
                _DetectedRow(
                    original_index=row_index,
                    cells=list(row.cells),
                )
            )

        return rows

    @staticmethod
    def _trim_wrapper_rows(
        rows: list[_DetectedRow],
        table_bbox,
    ) -> list[_DetectedRow]:
        """
        Remove false leading and trailing rows that consist
        of one cell spanning nearly the entire detected table.

        PyMuPDF sometimes absorbs text blocks immediately
        above or below a bordered table into the table.
        """

        normalized_rows = list(rows)

        while (
            len(normalized_rows) > 1
            and TableMapper._is_full_width_wrapper_row(
                row=normalized_rows[0],
                table_bbox=table_bbox,
            )
        ):
            normalized_rows.pop(0)

        while (
            len(normalized_rows) > 1
            and TableMapper._is_full_width_wrapper_row(
                row=normalized_rows[-1],
                table_bbox=table_bbox,
            )
        ):
            normalized_rows.pop()

        return normalized_rows

    @staticmethod
    def _is_full_width_wrapper_row(
        row: _DetectedRow,
        table_bbox,
    ) -> bool:
        """
        Return True when a row has only one visible cell and
        that cell spans almost the complete detected width.

        This check is used only for leading and trailing rows.
        """

        visible_cells = [
            cell
            for cell in row.cells
            if cell is not None
        ]

        if len(visible_cells) != 1:
            return False

        cell_bbox = visible_cells[0]

        table_width = max(
            float(table_bbox[2])
            - float(table_bbox[0]),
            1.0,
        )

        cell_width = max(
            float(cell_bbox[2])
            - float(cell_bbox[0]),
            0.0,
        )

        width_ratio = (
            cell_width / table_width
        )

        return (
            width_ratio
            >= TableMapper.FULL_WIDTH_THRESHOLD
        )

    @staticmethod
    def _calculate_table_bbox(
        rows: list[_DetectedRow],
        fallback_bbox,
    ):
        """
        Recalculate the table bounding box after false rows
        have been removed.
        """

        visible_cells = [
            cell
            for row in rows
            for cell in row.cells
            if cell is not None
        ]

        if not visible_cells:
            return fallback_bbox

        left = min(
            float(cell[0])
            for cell in visible_cells
        )

        top = min(
            float(cell[1])
            for cell in visible_cells
        )

        right = max(
            float(cell[2])
            for cell in visible_cells
        )

        bottom = max(
            float(cell[3])
            for cell in visible_cells
        )

        return (
            left,
            top,
            right,
            bottom,
        )

    @staticmethod
    def _map_cells(
        table: Table,
        rows: list[_DetectedRow],
        extracted_rows: list,
        pdf_page,
        page_number: int,
    ) -> None:
        """
        Convert normalized row rectangles and extracted text
        into TableCell models.
        """

        for normalized_row_index, detected_row in enumerate(
            rows
        ):
            original_row_index = (
                detected_row.original_index
            )

            for column_index in range(
                table.column_count
            ):
                cell_bbox = (
                    TableMapper._get_row_cell_bbox(
                        row=detected_row,
                        column_index=column_index,
                    )
                )

                if cell_bbox is None:
                    continue

                cell_text = (
                    TableMapper._get_cell_text(
                        extracted_rows=extracted_rows,
                        row_index=original_row_index,
                        column_index=column_index,
                    )
                )

                fill_color = TableMapper._detect_cell_fill_color(
                    pdf_page=pdf_page,
                    cell_bbox=cell_bbox,
                )
                
                table.cells.append(
                    TableCell(
                        page_number=page_number,

                        left=float(cell_bbox[0]),
                        top=float(cell_bbox[1]),
                        right=float(cell_bbox[2]),
                        bottom=float(cell_bbox[3]),

                        row_index=normalized_row_index,
                        column_index=column_index,

                        text=cell_text,
                        fill_color=fill_color,
                    )
                )

    @staticmethod
    def _detect_cell_fill_color(
        pdf_page,
        cell_bbox,
    ) -> str | None:
        """
        Detect a filled PDF rectangle covering most of a table cell.
    
        Thin line-like rectangles are ignored because they are
        table borders, not cell backgrounds.
        """
    
        cell_rect = fitz.Rect(
            cell_bbox
        )
    
        cell_area = max(
            cell_rect.width * cell_rect.height,
            1.0,
        )
    
        candidates: list[
            tuple[float, str]
        ] = []
    
        for drawing in pdf_page.get_drawings():
        
            fill_color = drawing.get(
                "fill"
            )
    
            drawing_rect_value = drawing.get(
                "rect"
            )
    
            if (
                fill_color is None
                or drawing_rect_value is None
            ):
                continue
            
            drawing_rect = fitz.Rect(
                drawing_rect_value
            )
    
            intersection = (
                drawing_rect & cell_rect
            )
    
            if intersection.is_empty:
                continue
            
            intersection_area = max(
                intersection.width
                * intersection.height,
                0.0,
            )
    
            coverage = (
                intersection_area / cell_area
            )
    
            if (
                coverage
                < TableMapper.CELL_FILL_MIN_COVERAGE
            ):
                continue
            
            # Ignore thin border rectangles.
            shorter_side = min(
                drawing_rect.width,
                drawing_rect.height,
            )
    
            if (
                shorter_side
                <= TableMapper.MAX_BORDER_THICKNESS
            ):
                continue
            
            candidates.append(
                (
                    coverage,
                    TableMapper._rgb_to_hex(
                        fill_color
                    ),
                )
            )
    
        if not candidates:
            return None
    
        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )
    
        detected_color = candidates[0][1]
    
        # White is equivalent to the page background and does
        # not need a dedicated filled shape.
        if detected_color == "#FFFFFF":
            return None
    
        return detected_color

    @staticmethod
    def _get_row_cell_bbox(
        row: _DetectedRow,
        column_index: int,
    ):
        """
        Return the cell rectangle at a column position while
        preserving PyMuPDF's None placeholders.
        """

        if column_index >= len(row.cells):
            return None

        return row.cells[column_index]

    @staticmethod
    def _get_cell_text(
        extracted_rows: list,
        row_index: int,
        column_index: int,
    ) -> str:
        """
        Safely retrieve extracted cell text using the
        original PyMuPDF row index.
        """

        if row_index >= len(extracted_rows):
            return ""

        extracted_row = extracted_rows[row_index]

        if extracted_row is None:
            return ""

        if column_index >= len(extracted_row):
            return ""

        value = extracted_row[column_index]

        if value is None:
            return ""

        return str(value).strip()
    
    @staticmethod
    def _detect_border_style(
        pdf_page,
        table_bbox,
    ) -> TableBorderStyle:
        """
        Detect the dominant table-border appearance.

        PDF producers may represent borders as either:

        1. stroked paths:
           - drawing["color"]
           - drawing["width"]

        2. thin filled rectangles:
           - drawing["fill"]
           - thickness derived from drawing["rect"]
        """

        table_rect = fitz.Rect(
            table_bbox
        )

        tolerance = (
            TableMapper.DRAWING_BBOX_TOLERANCE
        )

        expanded_table_rect = fitz.Rect(
            table_rect.x0 - tolerance,
            table_rect.y0 - tolerance,
            table_rect.x1 + tolerance,
            table_rect.y1 + tolerance,
        )

        detected_colors: list[str] = []
        detected_thicknesses: list[float] = []

        for drawing in pdf_page.get_drawings():

            drawing_rect_value = drawing.get(
                "rect"
            )

            if drawing_rect_value is None:
                continue

            drawing_rect = fitz.Rect(
                drawing_rect_value
            )

            if not TableMapper._rectangles_overlap(
                drawing_rect,
                expanded_table_rect,
            ):
                continue

            border_candidate = (
                TableMapper._extract_border_candidate(
                    drawing=drawing,
                    drawing_rect=drawing_rect,
                )
            )

            if border_candidate is None:
                continue

            border_color, border_thickness = (
                border_candidate
            )

            detected_colors.append(
                border_color
            )

            detected_thicknesses.append(
                border_thickness
            )

        if not detected_colors:
            return TableBorderStyle(
                color=TableMapper.DEFAULT_BORDER_COLOR,
                thickness=(
                    TableMapper.DEFAULT_BORDER_THICKNESS
                ),
            )

        dominant_color = Counter(
            detected_colors
        ).most_common(1)[0][0]

        dominant_thickness = float(
            median(detected_thicknesses)
        )

        dominant_thickness = min(
            max(
                dominant_thickness,
                TableMapper.MIN_BORDER_THICKNESS,
            ),
            TableMapper.MAX_BORDER_THICKNESS,
        )

        return TableBorderStyle(
            color=dominant_color,
            thickness=dominant_thickness,
        )

    @staticmethod
    def _extract_border_candidate(
        drawing: dict,
        drawing_rect: fitz.Rect,
    ) -> tuple[str, float] | None:
        """
        Extract border color and thickness from either a stroked
        path or a thin filled rectangle.
        """

        rectangle_width = max(
            float(drawing_rect.width),
            0.0,
        )

        rectangle_height = max(
            float(drawing_rect.height),
            0.0,
        )

        if (
            rectangle_width <= 0
            or rectangle_height <= 0
        ):
            return None

        shorter_side = min(
            rectangle_width,
            rectangle_height,
        )

        longer_side = max(
            rectangle_width,
            rectangle_height,
        )

        aspect_ratio = (
            longer_side
            / max(shorter_side, 0.001)
        )

        stroke_color = drawing.get(
            "color"
        )

        stroke_width = drawing.get(
            "width"
        )

        fill_color = drawing.get(
            "fill"
        )

        # Case 1: normal stroked PDF line.
        if (
            stroke_color is not None
            and stroke_width is not None
            and float(stroke_width) > 0
        ):
            thickness = float(
                stroke_width
            )

            if (
                thickness
                > TableMapper.MAX_BORDER_THICKNESS
            ):
                return None

            return (
                TableMapper._rgb_to_hex(
                    stroke_color
                ),
                thickness,
            )

        # Case 2: thin filled rectangle used as a line.
        if fill_color is None:
            return None

        if (
            aspect_ratio
            < TableMapper.MIN_LINE_ASPECT_RATIO
        ):
            return None

        if (
            shorter_side
            > TableMapper.MAX_BORDER_THICKNESS
        ):
            return None

        if TableMapper._is_nearly_white(
            fill_color
        ):
            return None

        return (
            TableMapper._rgb_to_hex(
                fill_color
            ),
            shorter_side,
        )

    @staticmethod
    def _rectangles_overlap(
        first: fitz.Rect,
        second: fitz.Rect,
    ) -> bool:
        """
        Return True when rectangles overlap or touch.

        This avoids relying on intersection.is_empty, which can
        reject extremely thin line-like rectangles.
        """

        return not (
            first.x1 < second.x0
            or first.x0 > second.x1
            or first.y1 < second.y0
            or first.y0 > second.y1
        )

    @staticmethod
    def _is_nearly_white(
        color,
    ) -> bool:
        """
        Ignore white page backgrounds and white cell fills.
        """

        if color is None or len(color) < 3:
            return False

        red = float(color[0])
        green = float(color[1])
        blue = float(color[2])

        return (
            red >= 0.95
            and green >= 0.95
            and blue >= 0.95
        )

    @staticmethod
    def _rgb_to_hex(
        color,
    ) -> str:
        """
        Convert PyMuPDF's 0–1 RGB tuple into a hexadecimal color.
        """

        if len(color) < 3:
            return "#000000"

        red = TableMapper._color_component_to_int(
            color[0]
        )

        green = TableMapper._color_component_to_int(
            color[1]
        )

        blue = TableMapper._color_component_to_int(
            color[2]
        )

        return (
            f"#{red:02X}"
            f"{green:02X}"
            f"{blue:02X}"
        )

    @staticmethod
    def _color_component_to_int(
        component: float,
    ) -> int:
        """
        Convert one normalized PDF color component into 0–255.
        """

        component = min(
            max(float(component), 0.0),
            1.0,
        )

        return int(
            round(component * 255)
        )