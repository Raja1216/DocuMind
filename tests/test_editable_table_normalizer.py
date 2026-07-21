from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.analyzer.editable_table_normalizer import (
    EditableTableNormalizer,
)
from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableTableDisposition,
)
from src.models.geometry.rectangle import Rectangle
from src.models.page import Page
from src.models.table import Table
from src.models.table_border_style import TableBorderStyle
from src.models.table_cell import TableCell


def make_cell(
    row_index: int,
    column_index: int,
    left: float,
    top: float,
    right: float,
    bottom: float,
    text: str,
    row_span: int = 1,
    column_span: int = 1,
    fill_color: str | None = None,
) -> TableCell:
    return TableCell(
        page_number=1,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        row_index=row_index,
        column_index=column_index,
        text=text,
        row_span=row_span,
        column_span=column_span,
        fill_color=fill_color,
    )


def make_complete_table() -> Table:
    table = Table(
        page_number=1,
        left=50.0,
        top=100.0,
        right=350.0,
        bottom=180.0,
        row_count=2,
        column_count=2,
        border_style=TableBorderStyle(
            color="#112233",
            thickness=1.25,
        ),
    )

    table.cells.extend(
        [
            make_cell(0, 0, 50.0, 100.0, 200.0, 140.0, "A"),
            make_cell(0, 1, 200.0, 100.0, 350.0, 140.0, "B"),
            make_cell(1, 0, 50.0, 140.0, 200.0, 180.0, "C"),
            make_cell(
                1,
                1,
                200.0,
                140.0,
                350.0,
                180.0,
                "D",
                fill_color="#ABCDEF",
            ),
        ]
    )

    return table


class EditableTableNormalizerTests(
    unittest.TestCase
):
    def test_complete_source_table_becomes_editable(
        self,
    ) -> None:
        source = make_complete_table()

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=source,
                table_index=0,
            )
        )

        self.assertEqual(
            result.row_count,
            2,
        )

        self.assertEqual(
            result.column_count,
            2,
        )

        self.assertEqual(
            len(result.rows),
            2,
        )

        self.assertEqual(
            len(result.columns),
            2,
        )

        self.assertEqual(
            len(result.cells),
            4,
        )

        self.assertTrue(
            result.is_structurally_valid
        )

        self.assertEqual(
            result.disposition,
            EditableTableDisposition.EDITABLE,
        )

        self.assertGreaterEqual(
            result.confidence,
            0.90,
        )

    def test_text_fill_border_and_source_are_preserved(
        self,
    ) -> None:
        source = make_complete_table()

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=source
            )
        )

        cell = result.get_cell(
            1,
            1,
        )

        self.assertIsNotNone(
            cell
        )

        assert cell is not None

        self.assertEqual(
            cell.text,
            "D",
        )

        self.assertEqual(
            cell.fill_color,
            "ABCDEF",
        )

        self.assertIs(
            cell.source_cell,
            source.get_cell(1, 1),
        )

        self.assertEqual(
            cell.borders.top.style,
            EditableBorderLineStyle.SINGLE,
        )

        self.assertEqual(
            cell.borders.top.color,
            "112233",
        )

        self.assertEqual(
            cell.borders.top.width,
            1.25,
        )

    def test_explicit_merged_cell_covers_grid_positions(
        self,
    ) -> None:
        table = Table(
            page_number=1,
            left=50.0,
            top=100.0,
            right=350.0,
            bottom=180.0,
            row_count=2,
            column_count=2,
        )

        table.cells.extend(
            [
                make_cell(
                    0,
                    0,
                    50.0,
                    100.0,
                    350.0,
                    140.0,
                    "Merged heading",
                    column_span=2,
                ),
                make_cell(1, 0, 50.0, 140.0, 200.0, 180.0, "A"),
                make_cell(1, 1, 200.0, 140.0, 350.0, 180.0, "B"),
            ]
        )

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=table
            )
        )

        merged = result.get_cell(
            0,
            1,
        )

        self.assertIsNotNone(
            merged
        )

        assert merged is not None

        self.assertEqual(
            merged.column_span,
            2,
        )

        self.assertTrue(
            result.is_structurally_valid
        )

        self.assertEqual(
            result.disposition,
            EditableTableDisposition.EDITABLE,
        )

    def test_uncovered_grid_position_uses_visual_fallback(
        self,
    ) -> None:
        table = make_complete_table()
        table.cells.pop()

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=table
            )
        )

        self.assertFalse(
            result.is_structurally_valid
        )

        self.assertEqual(
            result.disposition,
            EditableTableDisposition.VISUAL_FALLBACK,
        )

        self.assertTrue(
            any(
                "uncovered positions"
                in warning
                for warning in result.warnings
            )
        )

    def test_invalid_duplicate_cell_is_skipped_safely(
        self,
    ) -> None:
        table = make_complete_table()
        table.cells.append(
            make_cell(
                0,
                0,
                50.0,
                100.0,
                200.0,
                140.0,
                "Duplicate",
            )
        )

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=table
            )
        )

        self.assertEqual(
            len(result.cells),
            4,
        )

        self.assertTrue(
            any(
                "Skipped invalid source cell"
                in warning
                for warning in result.warnings
            )
        )

    def test_empty_source_table_uses_visual_fallback(
        self,
    ) -> None:
        source = Table(
            page_number=1,
            left=50.0,
            top=100.0,
            right=350.0,
            bottom=180.0,
            row_count=2,
            column_count=2,
        )

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=source
            )
        )

        self.assertEqual(
            result.disposition,
            EditableTableDisposition.VISUAL_FALLBACK,
        )

        self.assertTrue(
            result.reasons
        )

    def test_page_normalization_replaces_stale_tables(
        self,
    ) -> None:
        page = Page(
            number=1,
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),
            rotation=0,
        )

        stale = SimpleNamespace(
            table_id="stale"
        )

        page.editable_tables.append(
            stale
        )

        source = make_complete_table()
        page.tables.append(
            source
        )

        result = (
            EditableTableNormalizer
            .normalize_page(
                page
            )
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertIs(
            page.editable_tables,
            result,
        )

        self.assertIs(
            result[0].source_table,
            source,
        )

        self.assertFalse(
            any(
                getattr(
                    table,
                    "table_id",
                    "",
                )
                == "stale"
                for table in page.editable_tables
            )
        )

    def test_zero_width_border_becomes_none(
        self,
    ) -> None:
        source = make_complete_table()
        source.border_style = TableBorderStyle(
            color="#000000",
            thickness=0.0,
        )

        result = (
            EditableTableNormalizer
            .normalize_table(
                source_table=source
            )
        )

        cell = result.cells[0]

        self.assertEqual(
            cell.borders.top.style,
            EditableBorderLineStyle.NONE,
        )

        self.assertEqual(
            cell.borders.top.width,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
