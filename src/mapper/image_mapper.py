from __future__ import annotations

from src.models.image import Image


class ImageMapper:
    """
    Maps a PyMuPDF image-block dictionary into a
    DocuMind Image model.
    """

    @staticmethod
    def map(
        block_data: dict,
        page_number: int,
    ) -> Image:
        bbox = block_data["bbox"]

        return Image(
            page_number=page_number,

            left=float(bbox[0]),
            top=float(bbox[1]),
            right=float(bbox[2]),
            bottom=float(bbox[3]),

            block_number=int(
                block_data["number"]
            ),

            image_bytes=bytes(
                block_data["image"]
            ),

            extension=str(
                block_data.get(
                    "ext",
                    "png",
                )
            ),

            pixel_width=int(
                block_data.get(
                    "width",
                    0,
                )
            ),

            pixel_height=int(
                block_data.get(
                    "height",
                    0,
                )
            ),

            x_resolution=int(
                block_data.get(
                    "xres",
                    72,
                )
            ),

            y_resolution=int(
                block_data.get(
                    "yres",
                    72,
                )
            ),

            bits_per_component=int(
                block_data.get(
                    "bpc",
                    8,
                )
            ),

            colorspace=int(
                block_data.get(
                    "colorspace",
                    0,
                )
            ),
        )