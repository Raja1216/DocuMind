from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.analyzer.page_profile_analyzer import (
    PageProfileAnalyzer,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page import Page
from src.models.page_profile import (
    ConversionMode,
    PageType,
)


def make_span(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    font_size: float = 12.0,
):
    return SimpleNamespace(
        text=text,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        font_size=font_size,
    )


def make_block(
    spans,
):
    line = SimpleNamespace(
        spans=list(spans)
    )

    return SimpleNamespace(
        lines=[line]
    )


def make_region(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
):
    return SimpleNamespace(
        text=text,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


class PageProfileAnalyzerTests(
    unittest.TestCase
):

    def test_simple_text_page(
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

        page.blocks.append(
            make_block([
                make_span(
                    text=(
                        "This is a normal editable "
                        "paragraph."
                    ),
                    left=60.0,
                    top=80.0,
                    right=500.0,
                    bottom=100.0,
                )
            ])
        )

        page.paragraph_regions.append(
            make_region(
                text=(
                    "This is a normal editable "
                    "paragraph."
                ),
                left=60.0,
                top=80.0,
                right=500.0,
                bottom=100.0,
            )
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.page_type,
            PageType.SIMPLE_TEXT,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.EDITABLE,
        )

        self.assertTrue(
            profile.has_extractable_text
        )

        self.assertFalse(
            profile.requires_ocr
        )

    def test_scanned_page(
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

        page.images.append(
            SimpleNamespace(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            )
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.page_type,
            PageType.SCANNED,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.OCR,
        )

        self.assertTrue(
            profile.requires_ocr
        )

        self.assertGreaterEqual(
            profile.image_coverage,
            0.99,
        )

    def test_designed_cover_page(
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

        page.blocks.append(
            make_block([
                make_span(
                    text="Large Document Title",
                    left=70.0,
                    top=120.0,
                    right=540.0,
                    bottom=190.0,
                    font_size=48.0,
                ),
                make_span(
                    text="Subtitle",
                    left=180.0,
                    top=220.0,
                    right=430.0,
                    bottom=245.0,
                    font_size=16.0,
                ),
            ])
        )

        page.paragraph_regions.extend([
            make_region(
                text="Large Document Title",
                left=70.0,
                top=120.0,
                right=540.0,
                bottom=190.0,
            ),
            make_region(
                text="Subtitle",
                left=180.0,
                top=220.0,
                right=430.0,
                bottom=245.0,
            ),
        ])

        page.vector_graphics.append(
            SimpleNamespace(
                left=0.0,
                top=500.0,
                right=612.0,
                bottom=792.0,
                category="decorative",
            )
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.page_type,
            PageType.DESIGNED_COVER,
        )

        self.assertEqual(
            profile.recommended_mode,
            ConversionMode.HYBRID,
        )

    def test_table_dominant_page(
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

        page.tables.append(
            SimpleNamespace(
                left=50.0,
                top=100.0,
                right=562.0,
                bottom=650.0,
            )
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.page_type,
            PageType.TABLE_DOMINANT,
        )

        self.assertGreater(
            profile.table_coverage,
            0.50,
        )

    def test_background_vector_is_ignored(
        self,
    ) -> None:
        page = Page(
            number=1,

            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=100.0,
            ),

            rotation=0,
        )

        page.vector_graphics.append(
            SimpleNamespace(
                left=0.0,
                top=0.0,
                right=100.0,
                bottom=100.0,
                category="background",
            )
        )

        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            profile.vector_coverage,
            0.0,
        )

    def test_normal_text_with_small_decoration_is_not_cover(
        self,
    ) -> None:
        page = Page(
            number=4,
    
            bbox=Rectangle(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,
            ),
    
            rotation=0,
        )
    
        body_spans = []
    
        for index in range(8):
            top = 80.0 + index * 30.0
    
            body_spans.append(
                make_span(
                    text=(
                        "This is ordinary document body text "
                        "used for page classification."
                    ),
                    left=60.0,
                    top=top,
                    right=540.0,
                    bottom=top + 18.0,
                    font_size=12.0,
                )
            )
    
            page.paragraph_regions.append(
                make_region(
                    text=(
                        "This is ordinary document body text "
                        "used for page classification."
                    ),
                    left=60.0,
                    top=top,
                    right=540.0,
                    bottom=top + 18.0,
                )
            )
    
        page.blocks.append(
            make_block(
                body_spans
            )
        )
    
        # Small decorative footer element.
        page.vector_graphics.append(
            SimpleNamespace(
                left=0.0,
                top=740.0,
                right=612.0,
                bottom=792.0,
                category="decorative",
            )
        )
    
        profile = (
            PageProfileAnalyzer
            .analyze_page(
                page
            )
        )
    
        self.assertNotEqual(
            profile.page_type,
            PageType.DESIGNED_COVER,
        )
    
        self.assertEqual(
            profile.page_type,
            PageType.SIMPLE_TEXT,
        )

if __name__ == "__main__":
    unittest.main()