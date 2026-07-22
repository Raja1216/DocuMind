from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.analyzer.editable_table_style_analyzer import (
    EditableTableStyleAnalyzer,
)
from src.models.color.rgb_color import RGBColor
from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableCellHorizontalAlignment,
    EditableCellVerticalAlignment,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableCellParagraph,
    EditableTableColumn,
    EditableTableRow,
)
from src.models.geometry.rectangle import Rectangle
from src.models.line import Line
from src.models.span import Span
from src.models.text_block import TextBlock
from src.models.text_run import TextRun


def make_span(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    font_size: float = 10.0,
) -> Span:
    return Span(
        text=text,
        font="Arial",
        font_size=font_size,
        color=RGBColor(0, 0, 0),
        flags=0,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        origin_x=left,
        origin_y=bottom,
    )


def make_block(
    number: int,
    spans: list[Span],
) -> TextBlock:
    return TextBlock(
        page_number=1,
        left=min(span.left for span in spans),
        top=min(span.top for span in spans),
        right=max(span.right for span in spans),
        bottom=max(span.bottom for span in spans),
        block_number=number,
        lines=[
            Line(spans=spans)
        ],
    )


def make_table(
    row_count: int = 1,
    column_count: int = 1,
) -> EditableTable:
    table = EditableTable(
        page_number=1,
        table_id="table:1:1",
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=float(column_count * 100),
            bottom=float(row_count * 40),
        ),
        row_count=row_count,
        column_count=column_count,
        confidence=0.90,
    )

    for row_index in range(row_count):
        table.add_row(
            EditableTableRow(
                row_index=row_index,
                top=float(row_index * 40),
                bottom=float((row_index + 1) * 40),
                confidence=0.95,
            )
        )

    for column_index in range(column_count):
        table.add_column(
            EditableTableColumn(
                column_index=column_index,
                left=float(column_index * 100),
                right=float((column_index + 1) * 100),
                confidence=0.95,
            )
        )

    return table


def make_cell(
    row_index: int = 0,
    column_index: int = 0,
    *,
    text: str = "Text",
    fill_color: str | None = None,
) -> EditableTableCell:
    return EditableTableCell(
        row_index=row_index,
        column_index=column_index,
        bbox=Rectangle(
            left=float(column_index * 100),
            top=float(row_index * 40),
            right=float((column_index + 1) * 100),
            bottom=float((row_index + 1) * 40),
        ),
        text=text,
        fill_color=fill_color,
        confidence=0.90,
    )


def make_page(
    table: EditableTable,
    *,
    blocks=None,
    vector_graphics=None,
):
    return SimpleNamespace(
        editable_tables=[table],
        blocks=list(blocks or []),
        vector_graphics=list(vector_graphics or []),
    )


def add_formatted_paragraph(
    cell: EditableTableCell,
    *,
    text: str,
    bold: bool,
    font_size: float = 10.0,
) -> None:
    cell.content_paragraphs.append(
        EditableTableCellParagraph(
            text=text,
            runs=[
                TextRun(
                    text=text,
                    font_name="Arial",
                    font_size=font_size,
                    color=RGBColor(0, 0, 0),
                    bold=bold,
                )
            ],
            confidence=0.95,
        )
    )


class EditableTableStyleAnalyzerTests(
    unittest.TestCase
):

    def test_left_top_alignment_and_padding_are_inferred(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell()
        table.add_cell(cell)

        page = make_page(
            table,
            blocks=[
                make_block(
                    1,
                    [
                        make_span(
                            "Text",
                            7.0,
                            8.0,
                            35.0,
                            18.0,
                        )
                    ],
                )
            ],
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.horizontal_alignment,
            EditableCellHorizontalAlignment.LEFT,
        )
        self.assertEqual(
            cell.vertical_alignment,
            EditableCellVerticalAlignment.TOP,
        )
        self.assertAlmostEqual(
            cell.padding.left,
            7.0,
        )
        self.assertAlmostEqual(
            cell.padding.top,
            8.0,
        )

    def test_center_alignment_is_inferred(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell()
        table.add_cell(cell)

        page = make_page(
            table,
            blocks=[
                make_block(
                    1,
                    [
                        make_span(
                            "Centered",
                            35.0,
                            14.0,
                            65.0,
                            26.0,
                        )
                    ],
                )
            ],
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.horizontal_alignment,
            EditableCellHorizontalAlignment.CENTER,
        )
        self.assertEqual(
            cell.vertical_alignment,
            EditableCellVerticalAlignment.CENTER,
        )
        self.assertAlmostEqual(
            cell.padding.left,
            cell.padding.right,
        )

    def test_right_bottom_alignment_is_inferred(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell()
        table.add_cell(cell)

        page = make_page(
            table,
            blocks=[
                make_block(
                    1,
                    [
                        make_span(
                            "Right",
                            70.0,
                            25.0,
                            95.0,
                            35.0,
                        )
                    ],
                )
            ],
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.horizontal_alignment,
            EditableCellHorizontalAlignment.RIGHT,
        )
        self.assertEqual(
            cell.vertical_alignment,
            EditableCellVerticalAlignment.BOTTOM,
        )
        self.assertAlmostEqual(
            cell.padding.right,
            5.0,
        )
        self.assertAlmostEqual(
            cell.padding.bottom,
            5.0,
        )

    def test_padding_is_clamped_to_word_safe_range(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell()
        table.add_cell(cell)

        page = make_page(
            table,
            blocks=[
                make_block(
                    1,
                    [
                        make_span(
                            "Text",
                            30.0,
                            2.0,
                            40.0,
                            12.0,
                        )
                    ],
                )
            ],
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.padding.left,
            12.0,
        )
        self.assertGreaterEqual(
            cell.padding.top,
            0.5,
        )

    def test_bold_leading_row_is_detected_as_header(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
        )

        for column_index in range(2):
            header = make_cell(
                0,
                column_index,
                text=f"Header {column_index}",
            )
            add_formatted_paragraph(
                header,
                text=header.text,
                bold=True,
            )
            table.add_cell(header)

            body = make_cell(
                1,
                column_index,
                text=f"Body {column_index}",
            )
            add_formatted_paragraph(
                body,
                text=body.text,
                bold=False,
            )
            table.add_cell(body)

        page = make_page(table)

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertTrue(
            table.rows[0].is_header
        )
        self.assertFalse(
            table.rows[1].is_header
        )

    def test_label_value_table_is_not_mistaken_for_header(
        self,
    ) -> None:
        table = make_table(
            row_count=2,
            column_count=2,
        )

        for row_index in range(2):
            label = make_cell(
                row_index,
                0,
                text=f"Label {row_index}",
            )
            add_formatted_paragraph(
                label,
                text=label.text,
                bold=True,
            )
            table.add_cell(label)

            value = make_cell(
                row_index,
                1,
                text=f"Value {row_index}",
            )
            add_formatted_paragraph(
                value,
                text=value.text,
                bold=False,
            )
            table.add_cell(value)

        page = make_page(table)

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertFalse(
            table.rows[0].is_header
        )

    def test_individual_top_border_is_detected_from_vector_line(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell()
        table.add_cell(cell)

        top_line = SimpleNamespace(
            left=0.0,
            top=0.0,
            right=100.0,
            bottom=0.0,
            drawing_type="line",
            stroke_color="#FF0000",
            fill_color=None,
            stroke_width=1.25,
            dash_pattern=None,
        )

        page = make_page(
            table,
            vector_graphics=[top_line],
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.borders.top.color,
            "FF0000",
        )
        self.assertAlmostEqual(
            cell.borders.top.width,
            1.25,
        )
        self.assertEqual(
            cell.borders.right.color,
            "B7B7B7",
        )

    def test_existing_fill_and_fallback_borders_are_preserved(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell(
            fill_color="#DDEEFF"
        )

        custom_border = EditableTableBorder(
            style=EditableBorderLineStyle.DOUBLE,
            color="123456",
            width=1.5,
            confidence=0.80,
        )
        cell.borders = EditableTableCellBorders(
            top=custom_border,
            right=custom_border,
            bottom=custom_border,
            left=custom_border,
        )
        table.add_cell(cell)

        page = make_page(table)

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            cell.fill_color,
            "DDEEFF",
        )
        self.assertEqual(
            cell.borders.left.style,
            EditableBorderLineStyle.DOUBLE,
        )
        self.assertEqual(
            cell.borders.left.color,
            "123456",
        )

    def test_empty_cell_uses_stable_default_padding_and_reanalysis(
        self,
    ) -> None:
        table = make_table()
        cell = make_cell(text="")
        table.add_cell(cell)

        page = make_page(table)

        EditableTableStyleAnalyzer.analyze_page(page)

        first_padding = (
            cell.padding.top,
            cell.padding.right,
            cell.padding.bottom,
            cell.padding.left,
        )

        EditableTableStyleAnalyzer.analyze_page(page)

        self.assertEqual(
            first_padding,
            (
                cell.padding.top,
                cell.padding.right,
                cell.padding.bottom,
                cell.padding.left,
            ),
        )
        self.assertEqual(
            first_padding,
            (2.0, 3.0, 2.0, 3.0),
        )


if __name__ == "__main__":
    unittest.main()
