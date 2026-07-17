from __future__ import annotations

from docx import Document as WordDocument
from docx.dml.color import RGBColor as WordRGBColor
from docx.enum.section import WD_SECTION
from docx.shared import Pt

from src.exporter.builders.run_builder import RunBuilder
from src.models.enums.block_type import BlockType
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_BREAK,
    WD_LINE_SPACING,
)

from docx.oxml.ns import qn
from src.exporter.font_name_resolver import (
    FontNameResolver,
)

from collections import Counter
from statistics import median


class DocxExporter:
    """
    Exports the analyzed DocuMind document model to DOCX.
    """

    DEFAULT_MARGIN = 36.0
    MINIMUM_MARGIN = 18.0

    @staticmethod
    def export(document, output_path: str) -> None:
        word_document = WordDocument()
        
        for page_index, page in enumerate(document.pages):

            section = DocxExporter._prepare_page_section(
                word_document=word_document,
                page_index=page_index,
            )

            DocxExporter._configure_page_geometry(
                section=section,
                page=page,
            )

            DocxExporter._configure_page_margins(
                section=section,
                page=page,
            )

            DocxExporter._render_page(
                word_document=word_document,
                page=page,
            )

        word_document.save(output_path)

    @staticmethod
    def _prepare_page_section(
        word_document,
        page_index: int,
    ):
        """
        Use the existing first section for PDF page 1.

        For each later PDF page, create a new Word section
        beginning on a new page.
        """

        if page_index == 0:
            return word_document.sections[0]

        return word_document.add_section(
            WD_SECTION.NEW_PAGE
        )

    @staticmethod
    def _configure_page_geometry(
        section,
        page,
    ) -> None:
        """
        Apply the PDF page width and height to the Word section.

        PDF coordinates and Word points both use 1/72 inch.
        """

        section.page_width = Pt(
            page.bbox.width
        )

        section.page_height = Pt(
            page.bbox.height
        )

    @staticmethod
    def _configure_page_margins(
        section,
        page,
    ) -> None:
        """
        Calculate margins from the editable paragraph regions.

        The first paragraph begins at the original PDF content
        boundary, while later paragraph positions are reproduced
        using paragraph spacing and indentation.
        """

        regions = [
            region
            for region in page.paragraph_regions
            if region.text.strip()
        ]

        if not regions:
            DocxExporter._apply_default_margins(
                section
            )
            return

        left_edge = min(
            region.left
            for region in regions
        )

        top_edge = min(
            region.top
            for region in regions
        )

        right_edge = max(
            region.right
            for region in regions
        )

        bottom_edge = max(
            region.bottom
            for region in regions
        )

        left_margin = max(
            left_edge,
            DocxExporter.MINIMUM_MARGIN,
        )

        top_margin = max(
            top_edge,
            DocxExporter.MINIMUM_MARGIN,
        )

        right_margin = max(
            page.bbox.width - right_edge,
            DocxExporter.MINIMUM_MARGIN,
        )

        bottom_margin = max(
            page.bbox.height - bottom_edge,
            DocxExporter.MINIMUM_MARGIN,
        )

        section.left_margin = Pt(
            left_margin
        )

        section.top_margin = Pt(
            top_margin
        )

        section.right_margin = Pt(
            right_margin
        )

        section.bottom_margin = Pt(
            bottom_margin
        )

        section.header_distance = Pt(0)
        section.footer_distance = Pt(0)
        section.gutter = Pt(0)

    @staticmethod
    def _apply_default_margins(section) -> None:
        """
        Apply fallback margins to pages without text blocks.
        """

        margin = Pt(
            DocxExporter.DEFAULT_MARGIN
        )

        section.left_margin = margin
        section.top_margin = margin
        section.right_margin = margin
        section.bottom_margin = margin

    @staticmethod
    def _render_page(
        word_document,
        page,
    ) -> None:
        """
        Render one PDF page using normal editable Word
        paragraphs.

        No VML textbox or absolutely positioned text shape is
        created here.
        """

        regions = sorted(
            [
                region
                for region in page.paragraph_regions
                if region.text.strip()
            ],
            key=lambda region: (
                region.top,
                region.left,
            ),
        )

        if not regions:
            return

        content_left = min(
            region.left
            for region in regions
        )

        content_right = max(
            region.right
            for region in regions
        )

        previous_region = None

        for region in regions:
            word_paragraph = (
                word_document.add_paragraph()
            )

            is_heading = (
                DocxExporter._region_is_heading(
                    page=page,
                    region=region,
                )
            )

            DocxExporter._apply_region_layout(
                word_paragraph=word_paragraph,
                page=page,
                region=region,
                previous_region=previous_region,
                content_left=content_left,
                content_right=content_right,
                is_heading=is_heading,
            )

            DocxExporter._render_paragraph_runs(
                word_paragraph=word_paragraph,
                paragraph=region,
            )

            previous_region = region

    @staticmethod
    def _apply_region_layout(
        word_paragraph,
        page,
        region,
        previous_region,
        content_left: float,
        content_right: float,
        is_heading: bool,
    ) -> None:
        """
        Reconstruct paragraph indentation, vertical spacing,
        alignment and line spacing using the PDF coordinates.
        """

        paragraph_format = (
            word_paragraph.paragraph_format
        )

        left_indent = max(
            region.left - content_left,
            0.0,
        )

        right_indent = max(
            content_right - region.right,
            0.0,
        )

        first_line_indent = (
            DocxExporter
            ._calculate_first_line_indent(
                region
            )
        )

        paragraph_format.left_indent = Pt(
            left_indent
        )

        paragraph_format.right_indent = Pt(
            right_indent
        )

        paragraph_format.first_line_indent = Pt(
            first_line_indent
        )

        if previous_region is None:
            spacing_before = 0.0
        else:
            spacing_before = max(
                region.top
                - previous_region.bottom,
                0.0,
            )

        paragraph_format.space_before = Pt(
            spacing_before
        )

        paragraph_format.space_after = Pt(0)

        line_spacing = (
            DocxExporter
            ._estimate_region_line_spacing(
                region
            )
        )

        paragraph_format.line_spacing_rule = (
            WD_LINE_SPACING.EXACTLY
        )

        paragraph_format.line_spacing = Pt(
            line_spacing
        )

        alignment = (
            DocxExporter
            ._resolve_region_alignment(
                page=page,
                region=region,
            )
        )

        DocxExporter._apply_alignment(
            word_paragraph=word_paragraph,
            alignment=alignment,
        )

        paragraph_format.keep_together = True
        paragraph_format.widow_control = False

        if is_heading:
            paragraph_format.keep_with_next = True

    @staticmethod
    def _calculate_first_line_indent(
        region,
    ) -> float:
        """
        Calculate first-line indentation from the first visible
        line of the region.
        """

        for line in region.lines:
            visible_spans = [
                span
                for span in line.spans
                if span.text.strip()
            ]

            if not visible_spans:
                continue

            first_line_left = min(
                span.left
                for span in visible_spans
            )

            return (
                first_line_left
                - region.left
            )

        return 0.0

    @staticmethod
    def _estimate_region_line_spacing(
        region,
    ) -> float:
        """
        Estimate line spacing using the original PDF line
        positions.

        For multiline regions, baseline movement between lines is
        preferred. For single-line regions, the extracted text
        height is used.
        """

        visible_lines = []

        for line in region.lines:
            visible_spans = [
                span
                for span in line.spans
                if span.text.strip()
            ]

            if not visible_spans:
                continue

            line_top = min(
                span.top
                for span in visible_spans
            )

            line_bottom = max(
                span.bottom
                for span in visible_spans
            )

            visible_lines.append({
                "top": line_top,
                "bottom": line_bottom,
                "height": max(
                    line_bottom - line_top,
                    1.0,
                ),
            })

        if not visible_lines:
            return 12.0

        line_advances = [
            current["top"] - previous["top"]

            for previous, current in zip(
                visible_lines,
                visible_lines[1:],
            )

            if (
                current["top"]
                - previous["top"]
            ) > 1.0
        ]

        if line_advances:
            return max(
                float(
                    median(
                        line_advances
                    )
                ),
                1.0,
            )

        line_heights = [
            line["height"]
            for line in visible_lines
        ]

        return max(
            float(
                median(
                    line_heights
                )
            ),
            1.0,
        )

    @staticmethod
    def _resolve_region_alignment(
        page,
        region,
    ) -> str:
        """
        Reuse alignment calculated for the source block
        paragraphs.

        A region can combine multiple PDF blocks, so the most
        frequently detected alignment is selected.
        """

        source_numbers = set(
            region.source_block_numbers
        )

        alignments: list[str] = []

        for block in page.blocks:
            if (
                block.block_number
                not in source_numbers
            ):
                continue

            for paragraph in block.paragraphs:
                if not paragraph.text.strip():
                    continue

                alignment = (
                    paragraph.style.alignment
                    or "left"
                )

                alignments.append(
                    str(alignment).lower()
                )

        if alignments:
            return (
                Counter(
                    alignments
                )
                .most_common(1)[0][0]
            )

        return str(
            getattr(
                region.style,
                "alignment",
                "left",
            )
            or "left"
        ).lower()

    @staticmethod
    def _region_is_heading(
        page,
        region,
    ) -> bool:
        """
        Determine whether a paragraph region originated from a
        heading or subtitle block.
        """
    
        source_numbers = set(
            region.source_block_numbers
        )
    
        return any(
            block.block_number
            in source_numbers
    
            and block.block_type
            in {
                BlockType.HEADING,
                BlockType.SUBTITLE,
            }
    
            for block in page.blocks
        )

    @staticmethod
    def _create_word_paragraph(
        word_document,
        block_type: BlockType,
    ):
        """
        Create a Word heading or normal paragraph.
        """

        if block_type == BlockType.HEADING:
            return word_document.add_heading(
                level=1
            )

        return word_document.add_paragraph()

    @staticmethod
    def _apply_paragraph_indentation(
        word_paragraph,
        paragraph,
    ) -> None:
        """
        Apply horizontal paragraph geometry reconstructed
        from the PDF.
        """

        paragraph_format = (
            word_paragraph.paragraph_format
        )

        paragraph_format.left_indent = Pt(
            paragraph.style.left_indent
        )

        paragraph_format.right_indent = Pt(
            paragraph.style.right_indent
        )

        paragraph_format.first_line_indent = Pt(
            paragraph.style.first_line_indent
        )

    @staticmethod
    def _apply_paragraph_spacing(
        word_paragraph,
        paragraph,
    ) -> None:
        """
        Apply reconstructed paragraph and line spacing.
        """

        paragraph_format = (
            word_paragraph.paragraph_format
        )

        paragraph_format.space_before = Pt(
            paragraph.style.spacing_before
        )

        paragraph_format.space_after = Pt(
            paragraph.style.spacing_after
        )

        if paragraph.style.line_spacing > 0:
            paragraph_format.line_spacing_rule = (
                WD_LINE_SPACING.EXACTLY
            )

            paragraph_format.line_spacing = Pt(
                paragraph.style.line_spacing
            )

    @staticmethod
    def _render_paragraph_runs(
        word_paragraph,
        paragraph,
    ) -> None:
        """
        Render text while preserving original PDF line
        boundaries and typography.

        PDF lines remain in one Word paragraph and are
        separated using soft line breaks.
        """

        visible_lines = [
            line
            for line in paragraph.lines
            if DocxExporter._line_has_text(line)
        ]

        for line_index, line in enumerate(
            visible_lines
        ):
            text_runs = RunBuilder.build(
                line
            )

            for text_run in text_runs:
                run = word_paragraph.add_run(
                    text_run.text
                )

                font = run.font

                font.size = Pt(
                    text_run.font_size
                )

                DocxExporter._apply_font_name(
                    run=run,
                    pdf_font_name=text_run.font_name,
                )

                font.color.rgb = WordRGBColor(
                    text_run.color.red,
                    text_run.color.green,
                    text_run.color.blue,
                )

                run.bold = text_run.bold
                run.italic = text_run.italic

            if line_index < len(visible_lines) - 1:
                break_run = word_paragraph.add_run()

                break_run.add_break(
                    WD_BREAK.LINE
                )
                
    @staticmethod
    def _apply_font_name(
        run,
        pdf_font_name: str,
    ) -> None:
        """
        Resolve and apply a PDF font name to every Word
        font slot.

        Setting only run.font.name is sometimes insufficient
        because Word stores separate font names for different
        character categories.
        """

        word_font_name = FontNameResolver.resolve(
            pdf_font_name
        )

        run.font.name = word_font_name

        run_properties = run._element.get_or_add_rPr()

        font_properties = run_properties.get_or_add_rFonts()

        font_properties.set(
            qn("w:ascii"),
            word_font_name,
        )

        font_properties.set(
            qn("w:hAnsi"),
            word_font_name,
        )

        font_properties.set(
            qn("w:eastAsia"),
            word_font_name,
        )

        font_properties.set(
            qn("w:cs"),
            word_font_name,
        )


    @staticmethod
    def _apply_alignment(
        word_paragraph,
        alignment: str,
    ) -> None:
        """
        Apply paragraph alignment.
        """

        if alignment == "center":
            word_paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )
            return

        if alignment == "right":
            word_paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.RIGHT
            )
            return

        if alignment == "justify":
            word_paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.JUSTIFY
            )
            return

        word_paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.LEFT
        )

    @staticmethod
    def _line_has_text(line) -> bool:
        """
        Return True when a PDF line contains visible text.
        """

        return any(
            span.text.strip()
            for span in line.spans
        )

    @staticmethod
    def _block_has_text(block) -> bool:
        """
        Return True when a block contains visible text.
        """

        return any(
            span.text.strip()
            for line in block.lines
            for span in line.spans
        )