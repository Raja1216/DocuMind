from src.models.document import Document


class ParagraphStyleAnalyzer:

    @staticmethod
    def analyze(document: Document):

        for page in document.pages:

            for block in page.blocks:

                for paragraph in block.paragraphs:

                    if not paragraph.lines:
                        continue

                    first_line = paragraph.lines[0]

                    paragraph.style.left_indent = first_line.left