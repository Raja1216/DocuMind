from src.models.page import Page


class PageExtractor:
    """
    Extract page information from a PDF document.
    """

    def extract(self, document) -> list[Page]:
        pages: list[Page] = []

        for index in range(len(document)):
            pdf_page = document.load_page(index)

            rect = pdf_page.rect

            pages.append(
                Page(
                    number=index + 1,
                    width=rect.width,
                    height=rect.height,
                    left=rect.x0,
                    top=rect.y0,
                    right=rect.x1,
                    bottom=rect.y1,
                    rotation=pdf_page.rotation,
                )
            )

        return pages