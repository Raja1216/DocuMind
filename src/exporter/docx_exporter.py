from docx import Document as WordDocument
from docx.enum.text import WD_BREAK
from src.analyzer.paragraph_analyzer import ParagraphAnalyzer


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

                paragraphs = ParagraphAnalyzer.analyze(block)
                for para in paragraphs:

                    word_paragraph = doc.add_paragraph()

                    word_paragraph.add_run(para.text)


        doc.save(output_path)