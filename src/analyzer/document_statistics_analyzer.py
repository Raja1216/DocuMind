from collections import Counter

from src.models.document import Document

class DocumentStatisticsAnalyzer:

    @staticmethod
    def analyze(document: Document):

        sizes = []

        for page in document.pages:
            for block in page.blocks:
                for line in block.lines:
                    for span in line.spans:
                        sizes.append(round(span.font_size, 1))

        if not sizes:
            return

        document.statistics.largest_font_size = max(sizes)

        document.statistics.smallest_font_size = min(sizes)

        document.statistics.most_common_font_size = (
            Counter(sizes).most_common(1)[0][0]
        )