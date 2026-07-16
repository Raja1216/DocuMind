from __future__ import annotations


class VectorGraphicExtractor:
    """
    Extracts vector drawing groups from one PyMuPDF page.
    """

    @staticmethod
    def extract(pdf_page) -> list[dict]:
        """
        Return normalized PyMuPDF drawing dictionaries.
        """

        drawings = pdf_page.get_drawings()

        if not drawings:
            return []

        return list(drawings)