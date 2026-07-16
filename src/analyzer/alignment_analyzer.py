from src.models.document import Document


class AlignmentAnalyzer:

    @staticmethod
    def analyze(document: Document):

        for page in document.pages:

            page_width = page.width

            for block in page.blocks:

                for para in block.paragraphs:

                    if not para.lines:
                        continue

                    first_span = para.lines[0].spans[0]

                    left = first_span.left

                    right = first_span.right

                    center = (left + right) / 2

                    if abs(center - page_width / 2) < 20:
                        para.style.alignment = "center"

                    elif left > page_width * 0.55:
                        para.style.alignment = "right"

                    else:
                        para.style.alignment = "left"