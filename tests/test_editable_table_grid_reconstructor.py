from __future__ import annotations

import unittest

from src.analyzer.editable_table_grid_reconstructor import (
    EditableTableGridReconstructor,
)
from src.models.editable_table import (
    EditableTable,
    EditableTableCell,
    EditableTableDisposition,
)
from src.models.geometry.rectangle import Rectangle


def make_table(
    row_count: int,
    column_count: int,
    *,
    right: float = 200.0,
    bottom: float = 90.0,
) -> EditableTable:
    return EditableTable(
        page_number=1,
        table_id="table:1:1",
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=right,
            bottom=bottom,
        ),
        row_count=row_count,
        column_count=column_count,
        confidence=0.80,
    )


def add_cell(
    table: EditableTable,
    row_index: int,
    column_index: int,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    row_span: int = 1,
    column_span: int = 1,
    text: str = "",
) -> EditableTableCell:
    cell = EditableTableCell(
        row_index=row_index,
        column_index=column_index,
        bbox=Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        row_span=row_span,
        column_span=column_span,
        text=text,
        confidence=0.90,
        source_cell=object(),
    )
    table.add_cell(cell)
    return cell


class EditableTableGridReconstructorTests(
    unittest.TestCase
):
    def test_missing_internal_row_boundary_is_interpolated(
        self,
    ) -> None:
        table = make_table(
            row_count=3,
            column_count=1,
            right=100.0,
            bottom=90.0,
        )

        add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            100.0,
            60.0,
            row_span=2,
        )
        add_cell(
            table,
            2,
            0,
            0.0,
            60.0,
            100.0,
            90.0,
        )

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(
            len(table.rows),
            3,
        )
        self.assertAlmostEqual(
            table.rows[0].bottom,
            30.0,
            places=2,
        )
        self.assertAlmostEqual(
            table.rows[1].bottom,
            60.0,
            places=2,
        )
        self.assertTrue(
            table.is_structurally_valid
        )

    def test_missing_internal_column_boundary_is_interpolated(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=3,
            right=300.0,
            bottom=30.0,
        )

        add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            200.0,
            30.0,
            column_span=2,
        )
        add_cell(
            table,
            0,
            2,
            200.0,
            0.0,
            300.0,
            30.0,
        )

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(
            len(table.columns),
            3,
        )
        self.assertAlmostEqual(
            table.columns[0].right,
            100.0,
            places=2,
        )
        self.assertAlmostEqual(
            table.columns[1].right,
            200.0,
            places=2,
        )

    def test_missing_blank_position_gets_synthetic_cell(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
            right=200.0,
            bottom=60.0,
        )

        add_cell(table, 0, 0, 0.0, 0.0, 100.0, 30.0, text="A")
        add_cell(table, 0, 1, 100.0, 0.0, 200.0, 30.0, text="B")
        add_cell(table, 1, 0, 0.0, 30.0, 100.0, 60.0, text="C")

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        repaired = table.get_cell(1, 1)

        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertTrue(repaired.is_synthetic)
        self.assertEqual(repaired.text, "")
        self.assertTrue(table.is_structurally_valid)
        self.assertEqual(
            table.disposition,
            EditableTableDisposition.EDITABLE,
        )

    def test_large_synthetic_ratio_keeps_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=3,
            column_count=3,
            right=300.0,
            bottom=90.0,
        )

        add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            100.0,
            30.0,
        )

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(
            len(table.cells),
            9,
        )
        self.assertEqual(
            table.disposition,
            EditableTableDisposition.VISUAL_FALLBACK,
        )

    def test_jittered_cell_edges_are_snapped_to_shared_grid(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
            right=200.0,
            bottom=60.0,
        )

        first = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            99.8,
            29.7,
        )
        second = add_cell(
            table,
            0,
            1,
            100.2,
            0.1,
            200.0,
            30.2,
        )
        add_cell(
            table,
            1,
            0,
            0.0,
            30.3,
            100.1,
            60.0,
        )
        add_cell(
            table,
            1,
            1,
            99.9,
            29.9,
            200.0,
            60.0,
        )

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertAlmostEqual(
            first.bbox.right,
            second.bbox.left,
            places=4,
        )
        self.assertAlmostEqual(
            table.rows[0].bottom,
            table.rows[1].top,
            places=4,
        )

    def test_explicit_merged_cell_is_preserved(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
            right=200.0,
            bottom=60.0,
        )

        merged = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            200.0,
            30.0,
            column_span=2,
            text="Heading",
        )
        add_cell(table, 1, 0, 0.0, 30.0, 100.0, 60.0)
        add_cell(table, 1, 1, 100.0, 30.0, 200.0, 60.0)

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(merged.column_span, 2)
        self.assertFalse(merged.is_synthetic)
        self.assertEqual(
            sum(cell.is_synthetic for cell in table.cells),
            0,
        )
        self.assertTrue(table.is_structurally_valid)

    def test_empty_table_is_not_fabricated(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
            right=200.0,
            bottom=60.0,
        )

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(table.cells, [])
        self.assertEqual(table.rows, [])
        self.assertEqual(table.columns, [])
        self.assertEqual(
            table.disposition,
            EditableTableDisposition.VISUAL_FALLBACK,
        )

    def test_reanalysis_does_not_duplicate_synthetic_cells(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
            right=200.0,
            bottom=60.0,
        )

        add_cell(table, 0, 0, 0.0, 0.0, 100.0, 30.0)
        add_cell(table, 0, 1, 100.0, 0.0, 200.0, 30.0)
        add_cell(table, 1, 0, 0.0, 30.0, 100.0, 60.0)

        EditableTableGridReconstructor.reconstruct_table(
            table
        )
        first_count = len(table.cells)

        EditableTableGridReconstructor.reconstruct_table(
            table
        )

        self.assertEqual(
            len(table.cells),
            first_count,
        )
        self.assertEqual(
            sum(cell.is_synthetic for cell in table.cells),
            1,
        )


if __name__ == "__main__":
    unittest.main()
