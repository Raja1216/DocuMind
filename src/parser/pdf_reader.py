import fitz


class PDFReader:
    """
    Responsible only for opening PDF documents.
    """

    def open(self, pdf_path: str):
        """
        Open a PDF file and return the PyMuPDF document object.
        """

        document = fitz.open(pdf_path)

        return document