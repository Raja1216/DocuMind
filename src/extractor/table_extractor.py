from __future__ import annotations


class TableExtractor:
    """
    Uses PyMuPDF table detection to find tables on one page.
    """

    @staticmethod
    def extract(pdf_page) -> list:
        """
        Return PyMuPDF table objects detected on the page.
        """

        table_finder = pdf_page.find_tables()

        if table_finder is None:
            return []

        return list(
            table_finder.tables
        )