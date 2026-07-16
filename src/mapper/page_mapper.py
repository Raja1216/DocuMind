from __future__ import annotations

from src.mapper.block_mapper import BlockMapper
from src.models.geometry.rectangle import Rectangle
from src.models.page import Page


class PageMapper:

    @staticmethod
    def map(pdf_page, page_dict) -> Page:

        rect = pdf_page.rect

        page = Page(
            number=pdf_page.number + 1,
            bbox=Rectangle(
                left=rect.x0,
                top=rect.y0,
                right=rect.x1,
                bottom=rect.y1,
            ),
            rotation=pdf_page.rotation,
        )

        for block in page_dict["blocks"]:

            if block["type"] != 0:
                continue

            page.blocks.append(
                BlockMapper.map(
                    block,
                    page.number,
                )
            )

        return page