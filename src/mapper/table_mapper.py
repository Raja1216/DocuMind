from __future__ import annotations

from src.models.table import Table
from src.models.table_cell import TableCell


class TableMapper:
    """
    Maps one PyMuPDF table into DocuMind table models.
    """

    @staticmethod
    def map(
        pymupdf_table,
        page_number: int,
    ) -> Table:
        bbox = pymupdf_table.bbox

        extracted_rows = (
            pymupdf_table.extract()
            or []
        )

        row_count = int(
            pymupdf_table.row_count
        )

        column_count = int(
            pymupdf_table.col_count
        )

        table = Table(
            page_number=page_number,

            left=float(bbox[0]),
            top=float(bbox[1]),
            right=float(bbox[2]),
            bottom=float(bbox[3]),

            row_count=row_count,
            column_count=column_count,
        )

        TableMapper._map_cells(
            table=table,
            pymupdf_table=pymupdf_table,
            extracted_rows=extracted_rows,
            page_number=page_number,
        )

        return table

    @staticmethod
    def _map_cells(
        table: Table,
        pymupdf_table,
        extracted_rows: list,
        page_number: int,
    ) -> None:
        """
        Convert detected cell rectangles and extracted text
        into TableCell models.
        """

        for row_index in range(
            table.row_count
        ):
            for column_index in range(
                table.column_count
            ):
                cell_bbox = (
                    TableMapper._get_cell_bbox(
                        pymupdf_table=pymupdf_table,
                        row_index=row_index,
                        column_index=column_index,
                    )
                )

                if cell_bbox is None:
                    continue

                cell_text = (
                    TableMapper._get_cell_text(
                        extracted_rows=extracted_rows,
                        row_index=row_index,
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

                        row_index=row_index,
                        column_index=column_index,

                        text=cell_text,
                    )
                )

    @staticmethod
    def _get_cell_bbox(
        pymupdf_table,
        row_index: int,
        column_index: int,
    ):
        """
        Return one cell rectangle from PyMuPDF.

        PyMuPDF exposes cells as a row-major flat sequence.
        Missing cells may be represented as None.
        """

        cell_index = (
            row_index
            * int(pymupdf_table.col_count)
            + column_index
        )

        cells = pymupdf_table.cells

        if cell_index >= len(cells):
            return None

        return cells[cell_index]

    @staticmethod
    def _get_cell_text(
        extracted_rows: list,
        row_index: int,
        column_index: int,
    ) -> str:
        """
        Safely retrieve the extracted text of one cell.
        """

        if row_index >= len(extracted_rows):
            return ""

        row = extracted_rows[row_index]

        if row is None:
            return ""

        if column_index >= len(row):
            return ""

        value = row[column_index]

        if value is None:
            return ""

        return str(value).strip()