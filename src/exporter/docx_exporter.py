from docx import Document as WordDocument
from src.models.enums.block_type import BlockType
from src.exporter.builders.run_builder import RunBuilder
from docx.shared import Pt


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
                        for line in para.lines:

                            runs = RunBuilder.build(line)

                            for text_run in runs:
                            
                                run = word_paragraph.add_run(text_run.text)

                                run.font.size = Pt(text_run.font_size)
                                
                                run.bold = text_run.bold
                                
                                run.italic = text_run.italic
                                
                                run.font.name = text_run.font_name
            if page_index < total_pages - 1:
                doc.add_page_break()        


        doc.save(output_path)