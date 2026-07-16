from docx import Document as WordDocument
from src.models.enums.block_type import BlockType


class DocxExporter:

    @staticmethod
    def export(document, output_path):

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
                for para in block.paragraphs:

                    if block.block_type == BlockType.HEADING:
                        word_paragraph = doc.add_heading(level=1)
                    else:
                        word_paragraph = doc.add_paragraph()

                    word_paragraph.add_run(para.text)
            if page_index < total_pages - 1:
                doc.add_page_break()        


        doc.save(output_path)