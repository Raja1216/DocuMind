from __future__ import annotations

from src.extractor.text_block_extractor import TextBlockExtractor
from src.mapper.page_mapper import PageMapper
from src.models.document import Document
from src.models.metadata import PDFMetadata


class DocumentMapper:

    @staticmethod
    def map(pdf_document) -> Document:

        document = Document(
            metadata=PDFMetadata()
        )

        extractor = TextBlockExtractor()

        for page_index in range(len(pdf_document)):

            pdf_page = pdf_document.load_page(page_index)

            page_dict = extractor.extract(pdf_page)

            page = PageMapper.map(
                pdf_page,
                page_dict,
            )

            document.pages.append(page)

        return document