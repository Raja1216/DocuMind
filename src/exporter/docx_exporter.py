from __future__ import annotations

from docx import Document as WordDocument
from docx.dml.color import RGBColor as WordRGBColor
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from src.exporter.builders.run_builder import RunBuilder
from src.models.enums.block_type import BlockType


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
                page=page,
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
        page,
        page_index: int,
    ):
        """
        Use the first existing section for PDF page 1.

        For every later PDF page, create a new Word section
        that starts on a new page.
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

        PDF coordinates and Word points both use 1/72 inch,
        so the extracted dimensions can be applied directly.
        """

        page_width = page.bbox.width
        page_height = page.bbox.height

        section.page_width = Pt(page_width)
        section.page_height = Pt(page_height)

    @staticmethod
    def _configure_page_margins(
        section,
        page,
    ) -> None:
        """
        Calculate Word margins from the visible text blocks
        on the corresponding PDF page.
        """

        content_blocks = [
            block
            for block in page.blocks
            if block.block_type != BlockType.PAGE_NUMBER
            and DocxExporter._block_has_text(block)
        ]

        if not content_blocks:
            DocxExporter._apply_default_margins(section)
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

        section.left_margin = Pt(left_margin)
        section.top_margin = Pt(top_margin)
        section.right_margin = Pt(right_margin)
        section.bottom_margin = Pt(bottom_margin)

    @staticmethod
    def _apply_default_margins(section) -> None:
        """
        Apply safe fallback margins when a page has no text.
        """

        margin = Pt(DocxExporter.DEFAULT_MARGIN)

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
        Render every supported text block on one page.
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
        Create the correct Word paragraph type.
        """

        if block_type == BlockType.HEADING:
            return word_document.add_heading(level=1)

        return word_document.add_paragraph()

    @staticmethod
    def _render_paragraph_runs(
        word_paragraph,
        paragraph,
    ) -> None:
        """
        Render the reconstructed paragraph while preserving
        text typography.
        """

        for line_index, line in enumerate(paragraph.lines):

            text_runs = RunBuilder.build(line)

            for text_run in text_runs:
                run = word_paragraph.add_run(
                    text_run.text
                )

                font = run.font

                font.size = Pt(
                    text_run.font_size
                )

                font.name = text_run.font_name

                font.color.rgb = WordRGBColor(
                    text_run.color.red,
                    text_run.color.green,
                    text_run.color.blue,
                )

                run.bold = text_run.bold
                run.italic = text_run.italic

            if line_index < len(paragraph.lines) - 1:
                word_paragraph.add_run(" ")

    @staticmethod
    def _apply_alignment(
        word_paragraph,
        alignment: str,
    ) -> None:
        """
        Apply analyzed paragraph alignment.
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
    def _block_has_text(block) -> bool:
        """
        Return True when a block contains visible text.
        """

        return any(
            span.text.strip()
            for line in block.lines
            for span in line.spans
        )