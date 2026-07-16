from __future__ import annotations

from dataclasses import dataclass

from src.models.table import Table
from src.models.table_cell import TableCell


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

    @staticmethod
    def map(
        pymupdf_table,
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

        TableMapper._map_cells(
            table=table,
            rows=normalized_rows,
            extracted_rows=extracted_rows,
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
                    )
                )

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