from __future__ import annotations

from src.extractor.table_extractor import TableExtractor
from src.mapper.block_mapper import BlockMapper
from src.mapper.image_mapper import ImageMapper
from src.mapper.table_mapper import TableMapper
from src.models.geometry.rectangle import Rectangle
from src.models.page import Page


class PageMapper:

    TEXT_BLOCK_TYPE = 0
    IMAGE_BLOCK_TYPE = 1

    @staticmethod
    def map(
        pdf_page,
        page_dict,
    ) -> Page:

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

        for block_data in page_dict["blocks"]:

            block_type = block_data.get(
                "type"
            )

            if (
                block_type
                == PageMapper.TEXT_BLOCK_TYPE
            ):
                page.blocks.append(
                    BlockMapper.map(
                        block_data,
                        page.number,
                    )
                )

                continue

            if (
                block_type
                == PageMapper.IMAGE_BLOCK_TYPE
            ):
                page.images.append(
                    ImageMapper.map(
                        block_data,
                        page.number,
                    )
                )
        
        detected_tables = TableExtractor.extract(
            pdf_page
        )

        for detected_table in detected_tables:
            page.tables.append(
                TableMapper.map(
                    pymupdf_table=detected_table,
                    pdf_page=pdf_page,
                    page_number=page.number,
                )
            )        

        return page