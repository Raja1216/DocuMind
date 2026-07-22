from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.editable_table_validator import (
    EditableTableValidator,
)
from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableColumn,
    EditableTableDisposition,
    EditableTableRow,
)
from src.models.editable_table_validation import (
    EditableTableRenderDecision,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


def make_border(
    style: EditableBorderLineStyle = (
        EditableBorderLineStyle.SINGLE
    ),
) -> EditableTableBorder:
    return EditableTableBorder(
        style=style,
        color="000000",
        width=(
            0.0
            if style
            == EditableBorderLineStyle.NONE
            else 0.5
        ),
        confidence=0.95,
    )


def make_borders(
    style: EditableBorderLineStyle = (
        EditableBorderLineStyle.SINGLE
    ),
) -> EditableTableCellBorders:
    return EditableTableCellBorders(
        top=make_border(style),
        right=make_border(style),
        bottom=make_border(style),
        left=make_border(style),
    )


def make_table(
    *,
    row_count: int = 3,
    column_count: int = 3,
    synthetic_positions: set[
        tuple[int, int]
    ] | None = None,
    border_style: EditableBorderLineStyle = (
        EditableBorderLineStyle.SINGLE
    ),
    source_table=None,
    table_id: str = "table:1:1",
) -> EditableTable:
    synthetic_positions = (
        synthetic_positions
        or set()
    )

    row_height = 30.0
    column_width = 80.0

    table = EditableTable(
        page_number=1,
        table_id=table_id,
        bbox=Rectangle(
            left=10.0,
            top=20.0,
            right=(
                10.0
                + column_count
                * column_width
            ),
            bottom=(
                20.0
                + row_count
                * row_height
            ),
        ),
        row_count=row_count,
        column_count=column_count,
        confidence=0.95,
        source_table=source_table,
    )

    for row_index in range(
        row_count
    ):
        table.add_row(
            EditableTableRow(
                row_index=row_index,
                top=(
                    20.0
                    + row_index
                    * row_height
                ),
                bottom=(
                    20.0
                    + (
                        row_index
                        + 1
                    )
                    * row_height
                ),
                confidence=0.95,
            )
        )

    for column_index in range(
        column_count
    ):
        table.add_column(
            EditableTableColumn(
                column_index=column_index,
                left=(
                    10.0
                    + column_index
                    * column_width
                ),
                right=(
                    10.0
                    + (
                        column_index
                        + 1
                    )
                    * column_width
                ),
                confidence=0.95,
            )
        )

    for row_index in range(
        row_count
    ):
        for column_index in range(
            column_count
        ):
            is_synthetic = (
                (
                    row_index,
                    column_index,
                )
                in synthetic_positions
            )

            table.add_cell(
                EditableTableCell(
                    row_index=row_index,
                    column_index=column_index,
                    bbox=Rectangle(
                        left=(
                            10.0
                            + column_index
                            * column_width
                        ),
                        top=(
                            20.0
                            + row_index
                            * row_height
                        ),
                        right=(
                            10.0
                            + (
                                column_index
                                + 1
                            )
                            * column_width
                        ),
                        bottom=(
                            20.0
                            + (
                                row_index
                                + 1
                            )
                            * row_height
                        ),
                    ),
                    text=(
                        ""
                        if is_synthetic
                        else (
                            f"R{row_index + 1}"
                            f"C{column_index + 1}"
                        )
                    ),
                    borders=make_borders(
                        border_style
                    ),
                    confidence=(
                        0.45
                        if is_synthetic
                        else 0.95
                    ),
                    is_synthetic=(
                        is_synthetic
                    ),
                )
            )

    return table


def issue_codes(
    report,
) -> set[str]:
    return {
        issue.code
        for issue in report.issues
    }


class EditableTableValidatorTests(
    unittest.TestCase
):

    def test_complete_ordinary_table_is_native_safe(
        self,
    ) -> None:
        report = (
            EditableTableValidator
            .validate_table(
                table=make_table(),
                available_width=500.0,
            )
        )

        self.assertEqual(
            report.decision,
            EditableTableRenderDecision
            .NATIVE_SAFE,
        )

        self.assertFalse(
            report.errors
        )

    def test_borderless_structurally_reliable_table_is_native(
        self,
    ) -> None:
        report = (
            EditableTableValidator
            .validate_table(
                table=make_table(
                    border_style=(
                        EditableBorderLineStyle
                        .NONE
                    )
                ),
                available_width=500.0,
            )
        )

        self.assertTrue(
            report.is_native
        )

    def test_valid_explicit_merged_table_is_native(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
        )

        # Replace the two top-row cells with one explicit merge.
        table.cells = [
            cell
            for cell in table.cells
            if cell.row_index != 0
        ]

        table.cells.append(
            EditableTableCell(
                row_index=0,
                column_index=0,
                bbox=Rectangle(
                    left=10.0,
                    top=20.0,
                    right=170.0,
                    bottom=50.0,
                ),
                text="Merged heading",
                column_span=2,
                borders=make_borders(),
                confidence=0.95,
            )
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=500.0,
            )
        )

        self.assertTrue(
            report.is_native
        )

        self.assertFalse(
            report.errors
        )

    def test_valid_inferred_merged_table_is_native(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
        )

        table.cells = [
            cell
            for cell in table.cells
            if cell.row_index != 0
        ]

        table.cells.append(
            EditableTableCell(
                row_index=0,
                column_index=0,
                bbox=Rectangle(
                    left=10.0,
                    top=20.0,
                    right=170.0,
                    bottom=50.0,
                ),
                text="Merged heading",
                column_span=2,
                borders=make_borders(),
                confidence=0.95,
                merge_inferred=True,
                merge_confidence=0.90,
            )
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=500.0,
            )
        )

        self.assertTrue(
            report.is_native
        )

    def test_minor_synthetic_repair_is_native_with_warning(
        self,
    ) -> None:
        table = make_table(
            row_count=4,
            column_count=4,
            synthetic_positions={
                (
                    3,
                    3,
                )
            },
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=500.0,
            )
        )

        self.assertEqual(
            report.decision,
            EditableTableRenderDecision
            .NATIVE_WITH_WARNINGS,
        )

        self.assertIn(
            "MINOR_SYNTHETIC_RECONSTRUCTION",
            issue_codes(
                report
            ),
        )

    def test_high_synthetic_ratio_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=4,
            column_count=4,
            synthetic_positions={
                (
                    row_index,
                    column_index,
                )
                for row_index in range(4)
                for column_index in range(4)
                if (
                    row_index
                    + column_index
                )
                % 2
                == 0
            },
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=500.0,
            )
        )

        self.assertEqual(
            report.decision,
            EditableTableRenderDecision
            .VISUAL_FALLBACK,
        )

        self.assertIn(
            "EXCESSIVE_SYNTHETIC_RECONSTRUCTION",
            issue_codes(
                report
            ),
        )

    def test_duplicate_anchor_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=1,
        )

        duplicate = EditableTableCell(
            row_index=0,
            column_index=0,
            bbox=Rectangle(
                left=10.0,
                top=20.0,
                right=90.0,
                bottom=50.0,
            ),
            text="Duplicate",
            borders=make_borders(),
            confidence=0.95,
        )

        # Direct mutation intentionally creates an invalid model.
        table.cells.append(
            duplicate
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertEqual(
            report.decision,
            EditableTableRenderDecision
            .VISUAL_FALLBACK,
        )

        self.assertIn(
            "DUPLICATE_CELL_ANCHOR",
            issue_codes(
                report
            ),
        )

    def test_overlapping_spans_use_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        first = table.cells[0]

        first.column_span = 2

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "OVERLAPPING_GRID_OWNERSHIP",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_merge_outside_grid_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        table.cells[0].column_span = 3

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "CELL_SPAN_OUTSIDE_GRID",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_missing_rows_use_visual_fallback(
        self,
    ) -> None:
        table = make_table()

        table.rows.pop()

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "INCOMPLETE_ROW_DEFINITIONS",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_missing_columns_use_visual_fallback(
        self,
    ) -> None:
        table = make_table()

        table.columns.pop()

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "INCOMPLETE_COLUMN_DEFINITIONS",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_zero_height_row_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table()

        table.rows[1].bottom = (
            table.rows[1].top
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "NON_POSITIVE_ROW_HEIGHT",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_zero_width_column_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table()

        table.columns[1].right = (
            table.columns[1].left
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "NON_POSITIVE_COLUMN_WIDTH",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_non_monotonic_geometry_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table()

        table.columns[1].left = (
            table.columns[0].right
            - 20.0
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "NON_MONOTONIC_COLUMN_GEOMETRY",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_rotated_table_uses_visual_fallback(
        self,
    ) -> None:
        table = make_table(
            source_table=SimpleNamespace(
                rotation=90.0
            )
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertIn(
            "ROTATED_TABLE_UNSUPPORTED",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_extremely_narrow_scaled_column_uses_fallback(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=3,
        )

        table.columns[0].right = 11.0

        table.columns[1].left = 11.0

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=100.0,
            )
        )

        self.assertIn(
            "RENDERED_COLUMN_TOO_NARROW",
            issue_codes(
                report
            ),
        )

        self.assertFalse(
            report.is_native
        )

    def test_empty_but_valid_real_cells_are_allowed(
        self,
    ) -> None:
        table = make_table()

        table.cells[0].text = ""

        report = (
            EditableTableValidator
            .validate_table(
                table=table
            )
        )

        self.assertTrue(
            report.is_native
        )

        self.assertNotIn(
            "INVALID_CELL_TEXT_TYPE",
            issue_codes(
                report
            ),
        )

    def test_large_ordinary_table_remains_native(
        self,
    ) -> None:
        table = make_table(
            row_count=40,
            column_count=10,
        )

        report = (
            EditableTableValidator
            .validate_table(
                table=table,
                available_width=900.0,
            )
        )

        self.assertTrue(
            report.is_native
        )

    def test_two_tables_on_one_page_get_independent_reports(
        self,
    ) -> None:
        first = make_table(
            table_id="table:1:1"
        )

        second = make_table(
            table_id="table:1:2",
            source_table=SimpleNamespace(
                rotation=90
            ),
        )

        page = SimpleNamespace(
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),
            editable_tables=[
                first,
                second,
            ],
            editable_table_validation_reports={
                "stale": object()
            },
        )

        reports = (
            EditableTableValidator
            .validate_page(
                page
            )
        )

        self.assertEqual(
            set(
                reports
            ),
            {
                "table:1:1",
                "table:1:2",
            },
        )

        self.assertTrue(
            reports[
                "table:1:1"
            ].is_native
        )

        self.assertFalse(
            reports[
                "table:1:2"
            ].is_native
        )

    def test_reanalysis_replaces_stale_reports(
        self,
    ) -> None:
        table = make_table()

        page = SimpleNamespace(
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),
            editable_tables=[
                table
            ],
            editable_table_validation_reports={
                "stale": object()
            },
        )

        first = (
            EditableTableValidator
            .validate_page(
                page
            )
        )

        first_report = first[
            table.table_id
        ]

        second = (
            EditableTableValidator
            .validate_page(
                page
            )
        )

        self.assertNotIn(
            "stale",
            second,
        )

        self.assertIsNot(
            first_report,
            second[
                table.table_id
            ],
        )

        self.assertEqual(
            first_report.decision,
            second[
                table.table_id
            ].decision,
        )


if __name__ == "__main__":
    unittest.main()
