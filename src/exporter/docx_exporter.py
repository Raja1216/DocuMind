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

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from src.exporter.font_name_resolver import (
    FontNameResolver,
)


class DocxExporter:
    """
    Exports the analyzed DocuMind document model to DOCX.
    """

    DEFAULT_MARGIN = 36.0
    MINIMUM_MARGIN = 18.0
    
    FIT_TEXT_START_ID = 1

    _fit_text_id = FIT_TEXT_START_ID

    @staticmethod
    def export(document, output_path: str) -> None:
        word_document = WordDocument()
        DocxExporter._fit_text_id = (
            DocxExporter.FIT_TEXT_START_ID
        )
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
        Calculate Word margins from visible text-block boundaries.
        """

        content_blocks = [
            block
            for block in page.blocks
            if (
                block.block_type != BlockType.PAGE_NUMBER
                and DocxExporter._block_has_text(block)
            )
        ]

        if not content_blocks:
            DocxExporter._apply_default_margins(
                section
            )
            return

        left_edge = min(
            block.left
            for block in content_blocks
        )

        top_edge = min(
            block.top
            for block in content_blocks
        )

        right_edge = max(
            block.right
            for block in content_blocks
        )

        bottom_edge = max(
            block.bottom
            for block in content_blocks
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
        Render all supported text blocks belonging to one PDF page.
        """

        for block in page.blocks:

            if not DocxExporter._block_has_text(block):
                continue

            if block.block_type == BlockType.PAGE_NUMBER:
                continue

            for paragraph in block.paragraphs:

                word_paragraph = (
                    DocxExporter._create_word_paragraph(
                        word_document=word_document,
                        block_type=block.block_type,
                    )
                )

                DocxExporter._apply_alignment(
                    word_paragraph=word_paragraph,
                    alignment=paragraph.style.alignment,
                )

                DocxExporter._apply_paragraph_spacing(
                    word_paragraph=word_paragraph,
                    paragraph=paragraph,
                )
                
                DocxExporter._apply_paragraph_indentation(
                    word_paragraph=word_paragraph,
                    paragraph=paragraph,
                )

                DocxExporter._render_paragraph_runs(
                    word_paragraph=word_paragraph,
                    paragraph=paragraph,
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
        Render text while preserving:

        - original PDF line boundaries;
        - typography;
        - original line width.

        All Word runs belonging to one PDF line receive the
        same fit-text ID and target width.
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

            line_width = DocxExporter._line_width(
                line
            )

            fit_text_id = (
                DocxExporter._next_fit_text_id()
            )

            created_runs = []

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

                created_runs.append(run)

            if line_width > 0:
                for run in created_runs:
                    DocxExporter._apply_fit_text(
                        run=run,
                        width_points=line_width,
                        fit_text_id=fit_text_id,
                    )

            if line_index < len(visible_lines) - 1:
                break_run = word_paragraph.add_run()

                break_run.add_break(
                    WD_BREAK.LINE
                )
    
    @staticmethod
    def _line_width(line) -> float:
        """
        Calculate the original visible width of one PDF line.

        The result is returned in points.
        """

        visible_spans = [
            span
            for span in line.spans
            if span.text.strip()
        ]

        if not visible_spans:
            return 0.0

        left = min(
            span.left
            for span in visible_spans
        )

        right = max(
            span.right
            for span in visible_spans
        )

        return max(
            right - left,
            0.0,
        )
        
    @staticmethod
    def _next_fit_text_id() -> int:
        """
        Return a unique ID used to group contiguous Word runs
        belonging to the same fitted PDF line.
        """

        current_id = DocxExporter._fit_text_id

        DocxExporter._fit_text_id += 1

        return current_id    
                
    @staticmethod
    def _apply_fit_text(
        run,
        width_points: float,
        fit_text_id: int,
    ) -> None:
        """
        Force a Word run group to occupy the original PDF
        line width.
    
        Word stores this width in twentieths of a point.
        """
    
        width_twips = max(
            int(round(width_points * 20)),
            1,
        )
    
        run_properties = (
            run._element.get_or_add_rPr()
        )
    
        existing_fit_text = run_properties.find(
            qn("w:fitText")
        )
    
        if existing_fit_text is not None:
            run_properties.remove(
                existing_fit_text
            )
    
        fit_text = OxmlElement(
            "w:fitText"
        )
    
        fit_text.set(
            qn("w:val"),
            str(width_twips),
        )
    
        fit_text.set(
            qn("w:id"),
            str(fit_text_id),
        )
    
        run_properties.append(
            fit_text
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