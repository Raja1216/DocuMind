from __future__ import annotations

from src.extractor.table_extractor import TableExtractor
from src.mapper.block_mapper import BlockMapper
from src.mapper.image_mapper import ImageMapper
from src.mapper.table_mapper import TableMapper
from src.models.geometry.rectangle import Rectangle
from src.models.page import Page

from src.extractor.vector_graphic_extractor import (
    VectorGraphicExtractor,
)
from src.mapper.vector_graphic_mapper import (
    VectorGraphicMapper,
)
from src.analyzer.vector_graphic_classifier import (
    VectorGraphicClassifier,
)
from src.analyzer.vector_graphic_grouper import (
    VectorGraphicGrouper,
)
from pathlib import Path

from src.renderer.vector_graphic_region_renderer import (
    VectorGraphicRegionRenderer,
)


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
            
        drawing_groups = (
            VectorGraphicExtractor.extract(
                pdf_page
            )
        )

        for sequence_number, drawing_data in enumerate(
            drawing_groups,
            start=1,
        ):
            vector_graphic = (
                VectorGraphicMapper.map(
                    drawing_data=drawing_data,
                    page_number=page.number,
                    sequence_number=sequence_number,
                )
            )

            if vector_graphic is None:
                continue
            
            if (
                PageMapper
                ._graphic_belongs_to_table(
                    vector_graphic=vector_graphic,
                    tables=page.tables,
                )
            ):
                continue
            
            page.vector_graphics.append(
                vector_graphic
            )            

        VectorGraphicClassifier.analyze_page(
            page
        )
        VectorGraphicGrouper.group(
            page
        )
        VectorGraphicRegionRenderer.render_page_regions(
            page=page,
            output_directory=Path(
                "debug_output"
            ) / "vector_regions",
            dpi=300,
        )
        
        return page
    
    @staticmethod
    def _graphic_belongs_to_table(
        vector_graphic,
        tables,
    ) -> bool:
        """
        Exclude drawings contained inside detected tables.
    
        Table borders and cell fills are already handled by the
        table engine and must not be rendered again by the
        vector-graphics engine.
        """
    
        graphic_center_x = (
            vector_graphic.left
            + vector_graphic.right
        ) / 2
    
        graphic_center_y = (
            vector_graphic.top
            + vector_graphic.bottom
        ) / 2
    
        for table in tables:
            if (
                table.left
                <= graphic_center_x
                <= table.right
                and table.top
                <= graphic_center_y
                <= table.bottom
            ):
                return True
    
        return False