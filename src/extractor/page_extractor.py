from src.models.page import Page


class PageExtractor:
    """
    Extract basic page information from a PDF document.
    """

    def extract(self, document) -> list[Page]:
        pages: list[Page] = []

        for page_number in range(len(document)):
            pdf_page = document.load_page(page_number)

            page = Page(
                number=page_number + 1,
                width=pdf_page.rect.width,
                height=pdf_page.rect.height,
            )

            pages.append(page)

        return pages