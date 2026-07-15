from __future__ import annotations


class TextBlockExtractor:
    """
    Extract raw text blocks from a PDF page.

    This class intentionally returns PyMuPDF data.
    We are studying the PDF structure before creating
    our own internal models.
    """

    def extract(self, pdf_page):
        return pdf_page.get_text("dict")