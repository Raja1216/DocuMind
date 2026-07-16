from __future__ import annotations

from docx import Document as WordDocument
from docx.dml.color import RGBColor as WordRGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from src.exporter.builders.run_builder import RunBuilder
from src.models.enums.block_type import BlockType


class DocxExporter:
    """
    Exports the analyzed DocuMind document model to DOCX.
    """

    @staticmethod
    def export(document, output_path: str) -> None:
        doc = WordDocument()

        total_pages = len(document.pages)

        for page_index, page in enumerate(document.pages):

            for block in page.blocks:

                has_text = any(
                    span.text.strip()
                    for line in block.lines
                    for span in line.spans
                )

                if not has_text:
                    continue

                if block.block_type == BlockType.PAGE_NUMBER:
                    continue

                for paragraph in block.paragraphs:

                    if block.block_type == BlockType.HEADING:
                        word_paragraph = doc.add_heading(level=1)
                    else:
                        word_paragraph = doc.add_paragraph()

                    DocxExporter._apply_alignment(
                        word_paragraph,
                        paragraph.style.alignment,
                    )

                    for line_index, line in enumerate(paragraph.lines):

                        text_runs = RunBuilder.build(line)

                        for text_run in text_runs:
                            run = word_paragraph.add_run(text_run.text)

                            run.font.size = Pt(text_run.font_size)
                            run.font.name = text_run.font_name

                            run.font.color.rgb = WordRGBColor(
                                text_run.color.red,
                                text_run.color.green,
                                text_run.color.blue,
                            )

                            run.bold = text_run.bold
                            run.italic = text_run.italic

                        if line_index < len(paragraph.lines) - 1:
                            word_paragraph.add_run(" ")

            if page_index < total_pages - 1:
                doc.add_page_break()

        doc.save(output_path)

    @staticmethod
    def _apply_alignment(word_paragraph, alignment: str) -> None:
        """
        Apply analyzed paragraph alignment to a Word paragraph.
        """

        if alignment == "center":
            word_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            return

        if alignment == "right":
            word_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            return

        if alignment == "justify":
            word_paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            return

        word_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT