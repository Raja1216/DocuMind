from __future__ import annotations

import unittest

from types import SimpleNamespace

from src.analyzer.page_render_plan_analyzer import (
    PageRenderPlanAnalyzer,
)
from src.models.geometry.rectangle import (
    Rectangle,
)
from src.models.page_render_plan import (
    PageRenderItem,
    PageRenderPlan,
    RenderDisposition,
    RenderItemKind,
    RenderItemRole,
    RenderPlacement,
)


def make_source(
    left: float,
    top: float,
    right: float,
    bottom: float,
    **attributes,
):
    values = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
    }

    values.update(
        attributes
    )

    return SimpleNamespace(
        **values
    )


def make_page():
    return SimpleNamespace(
        number=1,

        left=0.0,
        top=0.0,
        right=612.0,
        bottom=792.0,

        bbox=Rectangle(
            left=0.0,
            top=0.0,
            right=612.0,
            bottom=792.0,
        ),

        paragraph_regions=[],

        tables=[],

        table_regions=[],

        images=[],

        image_regions=[],

        charts=[],

        chart_regions=[],

        vector_graphic_regions=[],

        vector_regions=[],

        layout_regions=[],

        column_regions=[],

        reading_order_entries=[],

        conversion_policy=None,

        profile=None,

        render_plan=PageRenderPlan(
            page_number=1
        ),
    )


def add_paragraph(
    page,
    region_number: int,
    top: float,
    bottom: float,
    text: str,
    order: int,
    left: float = 50.0,
    right: float = 400.0,
    role: str = "body",
):
    paragraph = make_source(
        left=left,
        top=top,
        right=right,
        bottom=bottom,

        region_number=region_number,

        text=text,

        is_list_marker_only=False,
    )

    page.paragraph_regions.append(
        paragraph
    )

    page.reading_order_entries.append(
        SimpleNamespace(
            paragraph_region_number=(
                region_number
            ),

            order=order,

            role=role,

            layout_region_id=None,

            column_id=None,
        )
    )

    return paragraph


class PageRenderPlanAnalyzerTests(
    unittest.TestCase
):

    def test_combines_all_supported_item_kinds(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page=page,
            region_number=1,
            top=50.0,
            bottom=70.0,
            text="Introduction",
            order=1,
        )

        page.tables.append(
            make_source(
                left=50.0,
                top=100.0,
                right=400.0,
                bottom=180.0,

                table_number=1,

                confidence=0.90,
            )
        )

        page.images.append(
            make_source(
                left=50.0,
                top=220.0,
                right=400.0,
                bottom=350.0,

                image_number=1,
            )
        )

        page.charts.append(
            make_source(
                left=50.0,
                top=380.0,
                right=400.0,
                bottom=500.0,

                chart_number=1,
            )
        )

        page.vector_regions.append(
            make_source(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=80.0,

                region_number=1,

                category="background",
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        counts = (
            plan.count_by_kind()
        )

        self.assertEqual(
            counts[
                RenderItemKind.PARAGRAPH
            ],
            1,
        )

        self.assertEqual(
            counts[
                RenderItemKind.TABLE
            ],
            1,
        )

        self.assertEqual(
            counts[
                RenderItemKind.IMAGE
            ],
            1,
        )

        self.assertEqual(
            counts[
                RenderItemKind.CHART
            ],
            1,
        )

        self.assertEqual(
            counts[
                RenderItemKind.VECTOR
            ],
            1,
        )

    def test_paragraph_reading_order_is_preserved(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page=page,
            region_number=2,
            top=200.0,
            bottom=220.0,
            text="Second",
            order=2,
        )

        add_paragraph(
            page=page,
            region_number=1,
            top=100.0,
            bottom=120.0,
            text="First",
            order=1,
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        paragraph_items = [
            item

            for item in plan.items

            if item.kind
            == RenderItemKind.PARAGRAPH
        ]

        self.assertEqual(
            [
                item.source.text
                for item
                in paragraph_items
            ],
            [
                "First",
                "Second",
            ],
        )

    def test_table_is_inserted_between_paragraphs(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page=page,
            region_number=1,
            top=50.0,
            bottom=70.0,
            text="Before table",
            order=1,
        )

        add_paragraph(
            page=page,
            region_number=2,
            top=300.0,
            bottom=320.0,
            text="After table",
            order=2,
        )

        page.tables.append(
            make_source(
                left=50.0,
                top=120.0,
                right=400.0,
                bottom=250.0,

                table_number=1,

                confidence=0.90,
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        semantic_kinds = [
            item.kind

            for item in plan.items

            if item.placement
            != RenderPlacement.BACKGROUND
        ]

        self.assertEqual(
            semantic_kinds,
            [
                RenderItemKind.PARAGRAPH,
                RenderItemKind.TABLE,
                RenderItemKind.PARAGRAPH,
            ],
        )

    def test_marker_only_paragraph_is_skipped(
        self,
    ) -> None:
        page = make_page()

        paragraph = add_paragraph(
            page=page,
            region_number=1,
            top=100.0,
            bottom=115.0,
            text="•",
            order=1,
        )

        paragraph.is_list_marker_only = (
            True
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        item = plan.items_of_kind(
            RenderItemKind.PARAGRAPH
        )[0]

        self.assertEqual(
            item.disposition,
            RenderDisposition.SKIP,
        )

    def test_paragraph_covered_by_table_is_skipped(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page=page,
            region_number=1,
            top=120.0,
            bottom=140.0,
            text="Table cell text",
            order=1,
            left=80.0,
            right=250.0,
        )

        page.tables.append(
            make_source(
                left=50.0,
                top=100.0,
                right=400.0,
                bottom=250.0,

                table_number=1,

                confidence=0.95,
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        paragraph_item = (
            plan.items_of_kind(
                RenderItemKind.PARAGRAPH
            )[0]
        )

        self.assertEqual(
            paragraph_item.disposition,
            RenderDisposition.SKIP,
        )

        self.assertTrue(
            paragraph_item.reasons
        )

    def test_low_confidence_table_uses_visual_strategy(
        self,
    ) -> None:
        page = make_page()

        page.tables.append(
            make_source(
                left=50.0,
                top=100.0,
                right=400.0,
                bottom=250.0,

                table_number=1,

                confidence=0.30,
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        table_item = (
            plan.items_of_kind(
                RenderItemKind.TABLE
            )[0]
        )

        self.assertEqual(
            table_item.disposition,
            RenderDisposition.VISUAL,
        )

    def test_background_vector_is_background_visual(
        self,
    ) -> None:
        page = make_page()

        page.vector_regions.append(
            make_source(
                left=0.0,
                top=0.0,
                right=612.0,
                bottom=792.0,

                region_number=1,

                category="background",
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        vector_item = (
            plan.items_of_kind(
                RenderItemKind.VECTOR
            )[0]
        )

        self.assertEqual(
            vector_item.placement,
            RenderPlacement.BACKGROUND,
        )

        self.assertEqual(
            vector_item.disposition,
            RenderDisposition.VISUAL,
        )

    def test_chart_vector_is_promoted_to_chart(
        self,
    ) -> None:
        page = make_page()

        page.vector_regions.append(
            make_source(
                left=50.0,
                top=100.0,
                right=400.0,
                bottom=300.0,

                region_number=1,

                category="chart",
            )
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertEqual(
            len(
                plan.items_of_kind(
                    RenderItemKind.CHART
                )
            ),
            1,
        )

        self.assertEqual(
            len(
                plan.items_of_kind(
                    RenderItemKind.VECTOR
                )
            ),
            0,
        )

    def test_header_and_footer_are_not_body_flow_items(
        self,
    ) -> None:
        page = make_page()

        add_paragraph(
            page=page,
            region_number=1,
            top=20.0,
            bottom=35.0,
            text="Header",
            order=1,
            role="header",
        )

        add_paragraph(
            page=page,
            region_number=2,
            top=750.0,
            bottom=765.0,
            text="Footer",
            order=2,
            role="footer",
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        items = plan.items_of_kind(
            RenderItemKind.PARAGRAPH
        )

        self.assertEqual(
            items[0].role,
            RenderItemRole.HEADER,
        )

        self.assertEqual(
            items[0].placement,
            RenderPlacement.FLOATING,
        )

        self.assertEqual(
            items[1].role,
            RenderItemRole.FOOTER,
        )

        self.assertEqual(
            items[1].placement,
            RenderPlacement.FLOATING,
        )

    def test_reanalysis_removes_stale_items(
        self,
    ) -> None:
        page = make_page()

        page.render_plan.add_item(
            PageRenderItem(
                order=1,

                page_number=1,

                item_id="stale:1",

                kind=(
                    RenderItemKind.PARAGRAPH
                ),

                placement=(
                    RenderPlacement.FLOW
                ),

                disposition=(
                    RenderDisposition.EDITABLE
                ),

                role=(
                    RenderItemRole.BODY
                ),

                bbox=Rectangle(
                    left=0.0,
                    top=0.0,
                    right=10.0,
                    bottom=10.0,
                ),

                source=SimpleNamespace(),
            )
        )

        add_paragraph(
            page=page,
            region_number=1,
            top=100.0,
            bottom=120.0,
            text="Current paragraph",
            order=1,
        )

        plan = (
            PageRenderPlanAnalyzer
            .analyze_page(
                page
            )
        )

        self.assertFalse(
            any(
                item.item_id
                == "stale:1"

                for item in plan.items
            )
        )

        self.assertEqual(
            plan.item_count,
            1,
        )


if __name__ == "__main__":
    unittest.main()