from __future__ import annotations

import unittest

from src.analyzer.paragraph_region_analyzer import (
    ParagraphRegionAnalyzer,
    _LineRecord,
)
from src.models.color.rgb_color import RGBColor
from src.models.geometry.rectangle import Rectangle
from src.models.line import Line
from src.models.page import Page
from src.models.span import Span
from src.models.text_block import TextBlock
from types import SimpleNamespace


def make_span(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    font_size: float = 11.0,
) -> Span:
    return Span(
        text=text,
        font="Arial",
        font_size=font_size,
        color=RGBColor(
            red=0,
            green=0,
            blue=0,
        ),
        flags=0,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        origin_x=left,
        origin_y=bottom,
    )


def make_page() -> Page:
    return Page(
        number=1,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=612.0,
            bottom=792.0,
        ),
        rotation=0,
    )


def add_block(
    page: Page,
    block_number: int,
    spans: list[Span],
) -> None:
    page.blocks.append(
        TextBlock(
            page_number=page.number,
            left=min(
                span.left
                for span in spans
            ),
            top=min(
                span.top
                for span in spans
            ),
            right=max(
                span.right
                for span in spans
            ),
            bottom=max(
                span.bottom
                for span in spans
            ),
            block_number=block_number,
            lines=[
                Line(
                    spans=spans
                )
            ],
        )
    )
def make_list_test_span(
        text: str,
        left: float,
        right: float,
        top: float,
        font_size: float = 11.0,
    ):
        return SimpleNamespace(
            text=text,
            left=left,
            top=top,
            right=right,
            bottom=top + 12.0,
            font_size=font_size,
            font="Arial",
        )    


class ParagraphRegionAnalyzerTests(
    unittest.TestCase
):
    def test_numbered_list_wrapped_continuation_is_one_region(
        self,
    ) -> None:
        page = make_page()

        add_block(
            page=page,
            block_number=1,
            spans=[
                make_span(
                    text=(
                        "1. Open the template design "
                        "and recompile the"
                    ),
                    left=57.6,
                    top=100.0,
                    right=300.0,
                    bottom=112.0,
                )
            ],
        )

        add_block(
            page=page,
            block_number=2,
            spans=[
                make_span(
                    text=(
                        "template for the appropriate "
                        "presentment target."
                    ),
                    left=75.6,
                    top=113.5,
                    right=330.0,
                    bottom=125.5,
                )
            ],
        )

        ParagraphRegionAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.paragraph_regions),
            1,
        )

        region = page.paragraph_regions[0]

        self.assertEqual(
            region.list_marker,
            "1.",
        )

        self.assertEqual(
            region.list_type,
            "number",
        )

        self.assertEqual(
            len(region.lines),
            2,
        )

        self.assertEqual(
            region.text,
            (
                "1. Open the template design "
                "and recompile the\n"
                "template for the appropriate "
                "presentment target."
            ),
        )

    def test_bullet_list_wrapped_continuation_is_one_region(
        self,
    ) -> None:
        page = make_page()

        add_block(
            page=page,
            block_number=1,
            spans=[
                make_span(
                    text="• ",
                    left=75.6,
                    top=100.0,
                    right=83.4,
                    bottom=112.0,
                ),
                make_span(
                    text=(
                        "Identify the section "
                        "using the -abms"
                    ),
                    left=93.6,
                    top=100.0,
                    right=300.0,
                    bottom=112.0,
                ),
            ],
        )

        add_block(
            page=page,
            block_number=2,
            spans=[
                make_span(
                    text="command.",
                    left=93.6,
                    top=113.5,
                    right=145.0,
                    bottom=125.5,
                )
            ],
        )

        ParagraphRegionAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.paragraph_regions),
            1,
        )

        region = page.paragraph_regions[0]

        self.assertEqual(
            region.list_marker,
            "•",
        )

        self.assertEqual(
            len(region.lines),
            2,
        )

        self.assertEqual(
            region.text,
            (
                "• Identify the section "
                "using the -abms\n"
                "command."
            ),
        )

    def test_ordinary_indented_paragraph_is_not_merged(
        self,
    ) -> None:
        page = make_page()

        add_block(
            page=page,
            block_number=1,
            spans=[
                make_span(
                    text=(
                        "This is a complete ordinary "
                        "paragraph."
                    ),
                    left=57.6,
                    top=100.0,
                    right=280.0,
                    bottom=112.0,
                )
            ],
        )

        add_block(
            page=page,
            block_number=2,
            spans=[
                make_span(
                    text=(
                        "This separately indented paragraph "
                        "must remain separate."
                    ),
                    left=75.6,
                    top=113.5,
                    right=360.0,
                    bottom=125.5,
                )
            ],
        )

        ParagraphRegionAnalyzer.analyze_page(
            page
        )

        self.assertEqual(
            len(page.paragraph_regions),
            2,
        )

        self.assertEqual(
            page.paragraph_regions[0].text,
            (
                "This is a complete ordinary "
                "paragraph."
            ),
        )

        self.assertEqual(
            page.paragraph_regions[1].text,
            (
                "This separately indented paragraph "
                "must remain separate."
            ),
        )

    def test_supported_textual_marker_forms_are_recognized(
        self,
    ) -> None:
        markers = (
            "•",
            "1.",
            "1)",
            "1.2.",
            "a.",
            "B)",
            "(c)",
            "iv.",
            "(IV)",
        )

        for marker in markers:
            with self.subTest(
                marker=marker
            ):
                self.assertEqual(
                    (
                        ParagraphRegionAnalyzer
                        ._extract_textual_marker(
                            f"{marker} Item text"
                        )
                    ),
                    marker,
                )

    def test_numbered_list_wrapped_line_is_continuation(
        self,
    ) -> None:
        first = _LineRecord(
            spans=[
                make_list_test_span(
                    (
                        "1. Open the template design "
                        "ap_bookmark.IFD in Output Designer "
                        "and recompile the"
                    ),
                    50.0,
                    350.0,
                    100.0,
                )
            ],
            block_numbers={
                1
            },
        )

        continuation = _LineRecord(
            spans=[
                make_list_test_span(
                    (
                        "template for the appropriate "
                        "presentment target."
                    ),
                    68.0,
                    300.0,
                    114.0,
                )
            ],
            block_numbers={
                2
            },
        )

        self.assertTrue(
            ParagraphRegionAnalyzer
            ._is_continuation(
                group=[
                    first
                ],
                current=continuation,
            )
        )
    
    def test_bullet_list_wrapped_line_is_continuation(
        self,
    ) -> None:
        first = _LineRecord(
            spans=[
                make_list_test_span(
                    (
                        "• Identify the section for which "
                        "to generate bookmarks, if desired, "
                        "using the -abms"
                    ),
                    75.0,
                    390.0,
                    100.0,
                )
            ],
            block_numbers={
                1
            },
        )

        continuation = _LineRecord(
            spans=[
                make_list_test_span(
                    "command.",
                    92.0,
                    150.0,
                    114.0,
                )
            ],
            block_numbers={
                2
            },
        )

        self.assertTrue(
            ParagraphRegionAnalyzer
            ._is_continuation(
                group=[
                    first
                ],
                current=continuation,
            )
        )
    
    def test_separate_bullet_span_uses_content_span_left(
        self,
    ) -> None:
        first = _LineRecord(
            spans=[
                make_list_test_span(
                    "•",
                    50.0,
                    56.0,
                    100.0,
                ),

                make_list_test_span(
                    (
                        "Identify the bookmark file "
                        "using the -abmk"
                    ),
                    72.0,
                    260.0,
                    100.0,
                ),
            ],
            block_numbers={
                1
            },
        )

        continuation = _LineRecord(
            spans=[
                make_list_test_span(
                    "command.",
                    72.0,
                    135.0,
                    114.0,
                )
            ],
            block_numbers={
                2
            },
        )

        expected_left = (
            ParagraphRegionAnalyzer
            ._group_content_left(
                [
                    first
                ]
            )
        )

        self.assertAlmostEqual(
            expected_left,
            72.0,
            places=2,
        )

        self.assertTrue(
            ParagraphRegionAnalyzer
            ._is_continuation(
                group=[
                    first
                ],
                current=continuation,
            )
        )
    
    def test_complete_list_sentence_does_not_absorb_next_line(
        self,
    ) -> None:
        first = _LineRecord(
            spans=[
                make_list_test_span(
                    "•",
                    50.0,
                    56.0,
                    100.0,
                ),
    
                make_list_test_span(
                    (
                        "Identify the bookmark file "
                        "using the -abmk command."
                    ),
                    72.0,
                    320.0,
                    100.0,
                ),
            ],
            block_numbers={
                1
            },
        )
    
        next_paragraph = _LineRecord(
            spans=[
                make_list_test_span(
                    "Separate explanation.",
                    72.0,
                    210.0,
                    114.0,
                )
            ],
            block_numbers={
                2
            },
        )
    
        self.assertFalse(
            ParagraphRegionAnalyzer
            ._is_continuation(
                group=[
                    first
                ],
                current=next_paragraph,
            )
        )
    
    def test_normal_indented_paragraph_is_not_list_continuation(
        self,
    ) -> None:
        first = _LineRecord(
            spans=[
                make_list_test_span(
                    "Normal paragraph.",
                    50.0,
                    180.0,
                    100.0,
                )
            ],
            block_numbers={
                1
            },
        )

        separate = _LineRecord(
            spans=[
                make_list_test_span(
                    "Separate indented paragraph.",
                    85.0,
                    270.0,
                    114.0,
                )
            ],
            block_numbers={
                2
            },
        )

        self.assertFalse(
            ParagraphRegionAnalyzer
            ._is_continuation(
                group=[
                    first
                ],
                current=separate,
            )
        )
    
if __name__ == "__main__":
    unittest.main()