from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.analyzer.editable_table_content_assigner import (
    EditableTableContentAssigner,
)
from src.models.color.rgb_color import RGBColor
from src.models.editable_table import (
    EditableTable,
    EditableTableCell,
)
from src.models.geometry.rectangle import Rectangle
from src.models.line import Line
from src.models.span import Span
from src.models.text_block import TextBlock


def make_span(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    font: str = "Arial",
    font_size: float = 11.0,
    flags: int = 0,
) -> Span:
    return Span(
        text=text,
        font=font,
        font_size=font_size,
        color=RGBColor(0, 0, 0),
        flags=flags,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        origin_x=left,
        origin_y=bottom,
    )


def make_block(
    number: int,
    lines: list[list[Span]],
) -> TextBlock:
    all_spans = [
        span
        for line in lines
        for span in line
    ]

    return TextBlock(
        page_number=1,
        left=min(span.left for span in all_spans),
        top=min(span.top for span in all_spans),
        right=max(span.right for span in all_spans),
        bottom=max(span.bottom for span in all_spans),
        block_number=number,
        lines=[
            Line(spans=spans)
            for spans in lines
        ],
    )


def make_table(
    row_count: int = 1,
    column_count: int = 1,
    right: float = 300.0,
    bottom: float = 60.0,
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
        confidence=0.90,
    )


def add_cell(
    table: EditableTable,
    row_index: int,
    column_index: int,
    left: float,
    top: float,
    right: float,
    bottom: float,
    text: str = "",
    is_synthetic: bool = False,
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
        text=text,
        confidence=0.90,
        is_synthetic=is_synthetic,
    )
    table.add_cell(cell)
    return cell


def make_page(
    table: EditableTable,
    blocks: list[TextBlock],
    paragraph_regions=None,
):
    return SimpleNamespace(
        number=1,
        editable_tables=[table],
        blocks=blocks,
        paragraph_regions=list(
            paragraph_regions
            or []
        ),
    )


class EditableTableContentAssignerTests(
    unittest.TestCase
):
    def test_raw_span_text_replaces_damaged_extracted_text(
        self,
    ) -> None:
        table = make_table()
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            60.0,
            text="ap bookmark doc.pdf\n_ _",
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [[
                        make_span(
                            "ap_bookmark_doc.pdf ",
                            10.0,
                            15.0,
                            130.0,
                            27.0,
                        )
                    ]],
                )
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            cell.text,
            "ap_bookmark_doc.pdf",
        )
        self.assertEqual(
            len(cell.content_paragraphs),
            1,
        )
        self.assertEqual(
            cell.content_paragraphs[0].text,
            "ap_bookmark_doc.pdf",
        )

    def test_formatted_command_runs_are_preserved(
        self,
    ) -> None:
        table = make_table()
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            60.0,
            text="damaged",
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [[
                        make_span(
                            "-abmk",
                            10.0,
                            15.0,
                            40.0,
                            28.0,
                            font="Courier-Bold",
                            flags=(1 << 4),
                        ),
                        make_span(
                            "ap_bookmark.bmk",
                            40.02,
                            15.0,
                            130.0,
                            28.0,
                            font="Courier",
                        ),
                        make_span(
                            " -abms",
                            130.0,
                            15.0,
                            166.0,
                            28.0,
                            font="Courier-Bold",
                            flags=(1 << 4),
                        ),
                        make_span(
                            "invoices",
                            166.02,
                            15.0,
                            214.0,
                            28.0,
                            font="Courier",
                        ),
                    ]],
                )
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            cell.text,
            "-abmkap_bookmark.bmk -abmsinvoices",
        )

        runs = cell.content_paragraphs[0].runs

        self.assertEqual(
            [run.text for run in runs],
            [
                "-abmk",
                "ap_bookmark.bmk ",
                "-abms",
                "invoices",
            ],
        )
        self.assertTrue(runs[0].bold)
        self.assertFalse(runs[1].bold)
        self.assertTrue(runs[2].bold)
        self.assertFalse(runs[3].bold)

    def test_same_baseline_bullet_and_text_become_one_paragraph(
        self,
    ) -> None:
        table = make_table(bottom=100.0)
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            100.0,
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [
                        [
                            make_span(
                                "• ",
                                10.0,
                                10.0,
                                18.0,
                                23.0,
                                font="Symbol",
                            )
                        ],
                        [
                            make_span(
                                "First item ",
                                28.0,
                                10.2,
                                90.0,
                                23.2,
                            )
                        ],
                    ],
                ),
                make_block(
                    2,
                    [
                        [
                            make_span(
                                "• ",
                                10.0,
                                35.0,
                                18.0,
                                48.0,
                                font="Symbol",
                            )
                        ],
                        [
                            make_span(
                                "Second item ",
                                28.0,
                                35.2,
                                105.0,
                                48.2,
                            )
                        ],
                    ],
                ),
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            cell.text,
            "• First item\n• Second item",
        )
        self.assertEqual(
            len(cell.content_paragraphs),
            2,
        )
        self.assertTrue(
            all(
                paragraph.is_list_item
                for paragraph
                in cell.content_paragraphs
            )
        )
        self.assertEqual(
            [
                paragraph.list_marker
                for paragraph
                in cell.content_paragraphs
            ],
            ["•", "•"],
        )

    def test_wrapped_visual_lines_merge_into_one_cell_paragraph(
        self,
    ) -> None:
        table = make_table(bottom=80.0)
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            80.0,
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [[
                        make_span(
                            "A long table-cell sentence",
                            10.0,
                            10.0,
                            170.0,
                            23.0,
                        )
                    ]],
                ),
                make_block(
                    2,
                    [[
                        make_span(
                            "continues on the next line.",
                            10.0,
                            25.0,
                            165.0,
                            38.0,
                        )
                    ]],
                ),
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            len(cell.content_paragraphs),
            1,
        )
        self.assertEqual(
            cell.text,
            (
                "A long table-cell sentence "
                "continues on the next line."
            ),
        )

    def test_paragraph_region_provenance_is_attached(
        self,
    ) -> None:
        table = make_table()
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            60.0,
        )

        paragraph = SimpleNamespace(
            region_number=7,
            text="Cell paragraph",
            left=10.0,
            top=10.0,
            right=130.0,
            bottom=25.0,
            list_type=None,
            list_marker=None,
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [[
                        make_span(
                            "Cell paragraph",
                            10.0,
                            10.0,
                            130.0,
                            25.0,
                        )
                    ]],
                )
            ],
            paragraph_regions=[paragraph],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            cell.paragraph_region_numbers,
            [7],
        )
        self.assertIs(
            cell.paragraphs[0],
            paragraph,
        )
        self.assertEqual(
            cell.content_paragraphs[0]
            .paragraph_region_number,
            7,
        )

    def test_neighboring_cell_spans_are_not_mixed(
        self,
    ) -> None:
        table = make_table(
            column_count=2,
            right=200.0,
        )
        left_cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            100.0,
            60.0,
        )
        right_cell = add_cell(
            table,
            0,
            1,
            100.0,
            0.0,
            200.0,
            60.0,
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [
                        [
                            make_span(
                                "Left",
                                10.0,
                                15.0,
                                45.0,
                                28.0,
                            )
                        ],
                        [
                            make_span(
                                "Right",
                                120.0,
                                15.0,
                                160.0,
                                28.0,
                            )
                        ],
                    ],
                )
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(left_cell.text, "Left")
        self.assertEqual(right_cell.text, "Right")

    def test_reanalysis_replaces_stale_cell_content(
        self,
    ) -> None:
        table = make_table()
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            60.0,
            text="Old",
        )

        page = make_page(
            table,
            [
                make_block(
                    1,
                    [[
                        make_span(
                            "First",
                            10.0,
                            15.0,
                            50.0,
                            28.0,
                        )
                    ]],
                )
            ],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        page.blocks = [
            make_block(
                2,
                [[
                    make_span(
                        "Second",
                        10.0,
                        15.0,
                        60.0,
                        28.0,
                    )
                ]],
            )
        ]

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(cell.text, "Second")
        self.assertEqual(
            len(cell.content_paragraphs),
            1,
        )
        self.assertEqual(
            cell.content_paragraphs[0].text,
            "Second",
        )

    def test_extracted_text_is_retained_when_no_spans_exist(
        self,
    ) -> None:
        table = make_table()
        cell = add_cell(
            table,
            0,
            0,
            0.0,
            0.0,
            300.0,
            60.0,
            text="Fallback text",
        )

        page = make_page(
            table,
            [],
        )

        EditableTableContentAssigner.assign_page(
            page
        )

        self.assertEqual(
            cell.text,
            "Fallback text",
        )
        self.assertEqual(
            cell.content_paragraphs,
            [],
        )
        self.assertTrue(cell.warnings)


if __name__ == "__main__":
    unittest.main()
