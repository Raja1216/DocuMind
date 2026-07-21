from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableCellHorizontalAlignment,
    EditableCellVerticalAlignment,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableCellPadding,
    EditableTableColumn,
    EditableTableDisposition,
    EditableTableRow,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


def make_bbox(
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> Rectangle:
    return Rectangle(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


def make_cell(
    row_index: int,
    column_index: int,
    *,
    row_span: int = 1,
    column_span: int = 1,
    text: str = "",
) -> EditableTableCell:
    left = float(
        column_index * 100
    )

    top = float(
        row_index * 30
    )

    return EditableTableCell(
        row_index=row_index,
        column_index=column_index,
        row_span=row_span,
        column_span=column_span,
        bbox=make_bbox(
            left=left,
            top=top,
            right=(
                left
                + 100.0 * column_span
            ),
            bottom=(
                top
                + 30.0 * row_span
            ),
        ),
        text=text,
        confidence=0.90,
    )


def make_table(
    row_count: int = 2,
    column_count: int = 2,
) -> EditableTable:
    return EditableTable(
        page_number=1,
        table_id="table:1",
        bbox=make_bbox(
            50.0,
            100.0,
            450.0,
            300.0,
        ),
        row_count=row_count,
        column_count=column_count,
        confidence=0.85,
        source_table=SimpleNamespace(
            name="source"
        ),
    )


class EditableTableModelTests(
    unittest.TestCase
):

    def test_table_dimensions_and_confidence(
        self,
    ) -> None:
        table = make_table()

        self.assertEqual(
            table.width,
            400.0,
        )

        self.assertEqual(
            table.height,
            200.0,
        )

        table.set_confidence(
            5.0
        )

        self.assertEqual(
            table.confidence,
            1.0,
        )

        self.assertTrue(
            table.is_editable
        )

    def test_rows_and_columns_are_sorted(
        self,
    ) -> None:
        table = make_table()

        table.add_row(
            EditableTableRow(
                row_index=1,
                top=130.0,
                bottom=160.0,
            )
        )

        table.add_row(
            EditableTableRow(
                row_index=0,
                top=100.0,
                bottom=130.0,
                is_header=True,
            )
        )

        table.add_column(
            EditableTableColumn(
                column_index=1,
                left=250.0,
                right=450.0,
            )
        )

        table.add_column(
            EditableTableColumn(
                column_index=0,
                left=50.0,
                right=250.0,
            )
        )

        self.assertEqual(
            [
                row.row_index
                for row in table.rows
            ],
            [
                0,
                1,
            ],
        )

        self.assertEqual(
            [
                column.column_index
                for column in table.columns
            ],
            [
                0,
                1,
            ],
        )

        self.assertTrue(
            table.rows[0].is_header
        )

    def test_merged_cell_covers_grid_positions(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=3,
        )

        merged = make_cell(
            row_index=0,
            column_index=0,
            column_span=2,
            text="Merged heading",
        )

        table.add_cell(
            merged
        )

        table.add_cell(
            make_cell(
                row_index=0,
                column_index=2,
            )
        )

        table.add_cell(
            make_cell(
                row_index=1,
                column_index=0,
            )
        )

        table.add_cell(
            make_cell(
                row_index=1,
                column_index=1,
            )
        )

        table.add_cell(
            make_cell(
                row_index=1,
                column_index=2,
            )
        )

        self.assertIs(
            table.get_cell(
                0,
                1,
            ),
            merged,
        )

        self.assertTrue(
            table.is_structurally_valid
        )

    def test_overlapping_cells_are_rejected(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=3,
        )

        table.add_cell(
            make_cell(
                row_index=0,
                column_index=0,
                column_span=2,
            )
        )

        with self.assertRaises(
            ValueError
        ):
            table.add_cell(
                make_cell(
                    row_index=0,
                    column_index=1,
                )
            )

    def test_out_of_bounds_span_is_rejected(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
        )

        with self.assertRaises(
            ValueError
        ):
            table.add_cell(
                make_cell(
                    row_index=1,
                    column_index=1,
                    column_span=2,
                )
            )

    def test_missing_grid_positions_are_reported(
        self,
    ) -> None:
        table = make_table()

        table.add_cell(
            make_cell(
                row_index=0,
                column_index=0,
            )
        )

        errors = (
            table.validate_structure()
        )

        self.assertEqual(
            len(
                errors
            ),
            1,
        )

        self.assertIn(
            "uncovered positions",
            errors[0],
        )

        self.assertFalse(
            table.is_structurally_valid
        )

    def test_border_fill_padding_and_alignment_are_normalized(
        self,
    ) -> None:
        cell = EditableTableCell(
            row_index=0,
            column_index=0,
            bbox=make_bbox(
                0.0,
                0.0,
                100.0,
                30.0,
            ),
            text=" Header ",
            paragraph_region_numbers=[
                5,
                5,
                7,
            ],
            borders=EditableTableCellBorders(
                top=EditableTableBorder(
                    style=(
                        EditableBorderLineStyle
                        .DOUBLE
                    ),
                    color="#ff0000",
                    width=1.5,
                    confidence=2.0,
                )
            ),
            fill_color="#00ff00",
            horizontal_alignment=(
                EditableCellHorizontalAlignment
                .CENTER
            ),
            vertical_alignment=(
                EditableCellVerticalAlignment
                .CENTER
            ),
            padding=EditableTableCellPadding(
                top=-1.0,
                right=4.0,
                bottom=2.0,
                left=4.0,
            ),
        )

        self.assertEqual(
            cell.fill_color,
            "00FF00",
        )

        self.assertEqual(
            cell.borders.top.color,
            "FF0000",
        )

        self.assertEqual(
            cell.borders.top.confidence,
            1.0,
        )

        self.assertEqual(
            cell.padding.top,
            0.0,
        )

        self.assertEqual(
            cell.paragraph_region_numbers,
            [
                5,
                7,
            ],
        )

        self.assertEqual(
            cell.horizontal_alignment,
            (
                EditableCellHorizontalAlignment
                .CENTER
            ),
        )

    def test_none_border_forces_zero_width(
        self,
    ) -> None:
        border = EditableTableBorder(
            style=EditableBorderLineStyle.NONE,
            width=2.0,
        )

        self.assertEqual(
            border.width,
            0.0,
        )

    def test_disposition_and_messages(
        self,
    ) -> None:
        table = make_table()

        table.disposition = (
            EditableTableDisposition
            .VISUAL_FALLBACK
        )

        table.add_reason(
            "Grid confidence is low."
        )

        table.add_reason(
            "Grid confidence is low."
        )

        table.add_warning(
            "Merged cells are uncertain."
        )

        table.add_warning(
            "Merged cells are uncertain."
        )

        self.assertFalse(
            table.is_editable
        )

        self.assertEqual(
            table.reasons,
            [
                "Grid confidence is low."
            ],
        )

        self.assertEqual(
            table.warnings,
            [
                "Merged cells are uncertain."
            ],
        )


if __name__ == "__main__":
    unittest.main()
