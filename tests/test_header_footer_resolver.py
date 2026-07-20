from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.exporter.header_footer_resolver import (
    HeaderFooterResolver,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page import Page
from src.models.paragraph_alignment import (
    ParagraphAlignment,
)
from src.models.reading_order import (
    ReadingOrderEntry,
    ReadingOrderRole,
)


def make_page(
    number: int,
) -> Page:
    return Page(
        number=number,
        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=600.0,
            bottom=800.0,
        ),
        rotation=0,
    )


def add_paragraph(
    page: Page,
    number: int,
    text: str,
    top: float,
):
    page.paragraph_regions.append(
        SimpleNamespace(
            region_number=number,
            text=text,
            left=50.0,
            top=top,
            right=550.0,
            bottom=top + 20.0,
            lines=[],
            reading_order=number,
            detected_alignment=(
                ParagraphAlignment.CENTER
            ),
            alignment_confidence=0.90,
        )
    )


class HeaderFooterResolverTests(
    unittest.TestCase
):

    def test_page_numbers_share_section_signature(
        self,
    ) -> None:
        first_page = make_page(
            1
        )

        second_page = make_page(
            2
        )

        add_paragraph(
            first_page,
            1,
            "1",
            750.0,
        )

        add_paragraph(
            second_page,
            1,
            "2",
            750.0,
        )

        first_page.reading_order_entries.append(
            ReadingOrderEntry(
                order=1,
                page_number=1,
                paragraph_region_number=1,
                role=(
                    ReadingOrderRole.FOOTER
                ),
                bbox=Rectangle(
                    left=290.0,
                    top=750.0,
                    right=310.0,
                    bottom=770.0,
                ),
            )
        )

        second_page.reading_order_entries.append(
            ReadingOrderEntry(
                order=1,
                page_number=2,
                paragraph_region_number=1,
                role=(
                    ReadingOrderRole.FOOTER
                ),
                bbox=Rectangle(
                    left=290.0,
                    top=750.0,
                    right=310.0,
                    bottom=770.0,
                ),
            )
        )

        self.assertEqual(
            HeaderFooterResolver
            .section_signature(
                first_page
            ),
            HeaderFooterResolver
            .section_signature(
                second_page
            ),
        )

    def test_page_number_field_is_detected(
        self,
    ) -> None:
        paragraph_plan = SimpleNamespace(
            paragraph_region_number=1,
            paragraph=SimpleNamespace(
                text="Page 3 of 10"
            ),
        )

        field_plan = (
            HeaderFooterResolver
            ._parse_page_number_field(
                paragraph_plan
            )
        )

        self.assertIsNotNone(
            field_plan
        )

        self.assertEqual(
            field_plan.prefix,
            "Page ",
        )

        self.assertEqual(
            field_plan.separator.strip(),
            "of",
        )

        self.assertTrue(
            field_plan.include_total_pages
        )

    def test_normal_footer_text_is_not_page_field(
        self,
    ) -> None:
        paragraph_plan = SimpleNamespace(
            paragraph_region_number=1,
            paragraph=SimpleNamespace(
                text="Confidential"
            ),
        )

        field_plan = (
            HeaderFooterResolver
            ._parse_page_number_field(
                paragraph_plan
            )
        )

        self.assertIsNone(
            field_plan
        )


if __name__ == "__main__":
    unittest.main()