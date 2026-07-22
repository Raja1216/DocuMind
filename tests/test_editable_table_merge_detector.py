from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.editable_table_merge_detector import (
    EditableTableMergeDetector,
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
from src.models.geometry.rectangle import (
    Rectangle,
)


def make_borders(
    style: EditableBorderLineStyle = (
        EditableBorderLineStyle.NONE
    ),
) -> EditableTableCellBorders:
    width = (
        0.0

        if style
        == EditableBorderLineStyle.NONE

        else 0.5
    )

    def make_border():
        return EditableTableBorder(
            style=style,
            color="000000",
            width=width,
            confidence=0.95,
        )

    return EditableTableCellBorders(
        top=make_border(),
        right=make_border(),
        bottom=make_border(),
        left=make_border(),
    )


def make_table(
    row_count: int = 2,
    column_count: int = 2,
) -> EditableTable:
    table = EditableTable(
        page_number=1,

        table_id="table:1:1",

        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=float(
                column_count * 100
            ),
            bottom=float(
                row_count * 40
            ),
        ),

        row_count=row_count,

        column_count=column_count,

        confidence=0.90,
    )

    for row_index in range(
        row_count
    ):
        table.add_row(
            EditableTableRow(
                row_index=row_index,

                top=float(
                    row_index * 40
                ),

                bottom=float(
                    (row_index + 1)
                    * 40
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

                left=float(
                    column_index * 100
                ),

                right=float(
                    (column_index + 1)
                    * 100
                ),

                confidence=0.95,
            )
        )

    return table


def make_cell(
    row_index: int,
    column_index: int,
    *,
    text: str = "",
    is_synthetic: bool = False,
    source_bbox: Rectangle | None = None,
    row_span: int = 1,
    column_span: int = 1,
) -> EditableTableCell:
    cell_bbox = Rectangle(
        left=float(
            column_index * 100
        ),

        top=float(
            row_index * 40
        ),

        right=float(
            (
                column_index
                + column_span
            )
            * 100
        ),

        bottom=float(
            (
                row_index
                + row_span
            )
            * 40
        ),
    )

    source_cell = (
        None

        if is_synthetic

        else SimpleNamespace(
            bbox=(
                source_bbox
                if source_bbox is not None
                else cell_bbox
            )
        )
    )

    return EditableTableCell(
        row_index=row_index,

        column_index=column_index,

        bbox=cell_bbox,

        text=text,

        row_span=row_span,

        column_span=column_span,

        borders=make_borders(),

        confidence=0.90,

        source_cell=source_cell,

        is_synthetic=is_synthetic,
    )


class EditableTableMergeDetectorTests(
    unittest.TestCase
):

    def test_horizontal_merge_is_inferred(
        self,
    ) -> None:
        table = make_table()

        anchor = make_cell(
            0,
            0,

            text="Merged heading",

            source_bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=200.0,
                bottom=40.0,
            ),
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                0,
                1,
                is_synthetic=True,
            )
        )

        table.add_cell(
            make_cell(
                1,
                0,
                text="A",
            )
        )

        table.add_cell(
            make_cell(
                1,
                1,
                text="B",
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.column_span,
            2,
        )

        self.assertTrue(
            anchor.merge_inferred
        )

        self.assertTrue(
            anchor.is_merged
        )

        self.assertTrue(
            table.is_structurally_valid
        )

    def test_vertical_merge_is_inferred(
        self,
    ) -> None:
        table = make_table()

        anchor = make_cell(
            0,
            0,

            text="Merged label",

            source_bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=80.0,
            ),
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                1,
                0,
                is_synthetic=True,
            )
        )

        table.add_cell(
            make_cell(
                0,
                1,
                text="A",
            )
        )

        table.add_cell(
            make_cell(
                1,
                1,
                text="B",
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.row_span,
            2,
        )

        self.assertTrue(
            anchor.merge_inferred
        )

        self.assertTrue(
            table.is_structurally_valid
        )

    def test_two_by_two_merge_is_inferred(
        self,
    ) -> None:
        table = make_table()

        anchor = make_cell(
            0,
            0,

            text="Merged block",

            source_bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=200.0,
                bottom=80.0,
            ),
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                0,
                1,
                is_synthetic=True,
            )
        )

        table.add_cell(
            make_cell(
                1,
                0,
                is_synthetic=True,
            )
        )

        table.add_cell(
            make_cell(
                1,
                1,
                is_synthetic=True,
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.row_span,
            2,
        )

        self.assertEqual(
            anchor.column_span,
            2,
        )

        self.assertEqual(
            len(table.cells),
            1,
        )

        self.assertTrue(
            table.is_structurally_valid
        )

    def test_real_neighbor_blocks_merge(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        anchor = make_cell(
            0,
            0,

            text="Left",

            source_bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=200.0,
                bottom=40.0,
            ),
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                0,
                1,
                text="Right",
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.column_span,
            1,
        )

        self.assertFalse(
            anchor.merge_inferred
        )

        self.assertEqual(
            table.disposition,
            EditableTableDisposition
            .VISUAL_FALLBACK,
        )

    def test_synthetic_blank_cell_is_not_merged_without_geometry(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        anchor = make_cell(
            0,
            0,
            text="Normal cell",
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                0,
                1,
                is_synthetic=True,
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.column_span,
            1,
        )

        self.assertFalse(
            anchor.merge_inferred
        )

        self.assertEqual(
            len(table.cells),
            2,
        )

    def test_explicit_merge_is_preserved(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        anchor = make_cell(
            0,
            0,
            text="Explicit merge",
            column_span=2,
        )

        table.add_cell(
            anchor
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            anchor.column_span,
            2,
        )

        self.assertFalse(
            anchor.merge_inferred
        )

        self.assertTrue(
            anchor.is_merged
        )

    def test_detection_is_idempotent(
        self,
    ) -> None:
        table = make_table(
            row_count=1,
            column_count=2,
        )

        anchor = make_cell(
            0,
            0,

            text="Merged heading",

            source_bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=200.0,
                bottom=40.0,
            ),
        )

        table.add_cell(
            anchor
        )

        table.add_cell(
            make_cell(
                0,
                1,
                is_synthetic=True,
            )
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        first_cell_count = len(
            table.cells
        )

        EditableTableMergeDetector.detect_table(
            table
        )

        self.assertEqual(
            len(table.cells),
            first_cell_count,
        )

        self.assertEqual(
            anchor.column_span,
            2,
        )


if __name__ == "__main__":
    unittest.main()