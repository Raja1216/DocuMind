from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from src.models.vector_graphic import VectorGraphic
from src.models.vector_graphic_region import VectorGraphicRegion


class VectorGraphicRegionRenderer:
    """
    Renders grouped PDF vector drawings into isolated,
    transparent PNG images.

    Text, raster images, and unrelated page content are not
    included because only the original drawing commands are
    replayed.
    """

    DEFAULT_DPI = 300
    DEFAULT_PADDING = 2.0

    @classmethod
    def render_page_regions(
        cls,
        page,
        output_directory: str | Path,
        dpi: int = DEFAULT_DPI,
        padding: float = DEFAULT_PADDING,
    ) -> None:
        """
        Render every vector region belonging to one mapped page.
        """

        output_path = Path(output_directory)

        page_output_path = (
            output_path
            / f"page_{page.number}"
        )

        page_output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        for region in page.vector_regions:
            cls.render_region(
                region=region,
                output_directory=page_output_path,
                dpi=dpi,
                padding=padding,
            )

    @classmethod
    def render_region(
        cls,
        region: VectorGraphicRegion,
        output_directory: str | Path,
        dpi: int = DEFAULT_DPI,
        padding: float = DEFAULT_PADDING,
    ) -> Path:
        """
        Render one grouped vector region to a transparent PNG.
        """

        if not region.graphics:
            raise ValueError(
                "Cannot render a vector region without graphics."
            )

        output_path = Path(output_directory)

        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        region_width = max(
            region.right - region.left,
            1.0,
        )

        region_height = max(
            region.bottom - region.top,
            1.0,
        )

        canvas_width = region_width + padding * 2
        canvas_height = region_height + padding * 2
        
        region.image_left = (
            region.left - padding
        )
        
        region.image_top = (
            region.top - padding
        )
        
        region.image_width = canvas_width
        region.image_height = canvas_height

        temporary_document = pymupdf.open()

        try:
            temporary_page = temporary_document.new_page(
                width=canvas_width,
                height=canvas_height,
            )

            offset_x = -region.left + padding
            offset_y = -region.top + padding

            rendered_count = 0

            for graphic in region.graphics:
                if cls._render_graphic(
                    page=temporary_page,
                    graphic=graphic,
                    offset_x=offset_x,
                    offset_y=offset_y,
                ):
                    rendered_count += 1

            if rendered_count == 0:
                raise ValueError(
                    "The vector region did not contain any "
                    "renderable drawing commands."
                )

            matrix_scale = dpi / 72.0

            matrix = pymupdf.Matrix(
                matrix_scale,
                matrix_scale,
            )

            pixmap = temporary_page.get_pixmap(
                matrix=matrix,
                alpha=True,
            )

            image_path = (
                output_path
                / (
                    f"vector_region_"
                    f"{region.region_number}.png"
                )
            )

            pixmap.save(
                str(image_path)
            )

            region.image_path = str(
                image_path.resolve()
            )

            return image_path

        finally:
            temporary_document.close()

    @classmethod
    def _render_graphic(
        cls,
        page: pymupdf.Page,
        graphic: VectorGraphic,
        offset_x: float,
        offset_y: float,
    ) -> bool:
        """
        Replay one PyMuPDF drawing dictionary onto a new page.
        """

        drawing = graphic.source_drawing

        if not drawing:
            return False

        items = drawing.get("items") or []

        if not items:
            return False

        shape = page.new_shape()

        drawn_items = 0

        for item in items:
            if not item:
                continue

            operation = item[0]

            try:
                if operation == "l":
                    cls._draw_line(
                        shape,
                        item,
                        offset_x,
                        offset_y,
                    )

                elif operation == "c":
                    cls._draw_curve(
                        shape,
                        item,
                        offset_x,
                        offset_y,
                    )

                elif operation == "re":
                    cls._draw_rectangle(
                        shape,
                        item,
                        offset_x,
                        offset_y,
                    )

                elif operation == "qu":
                    cls._draw_quad(
                        shape,
                        item,
                        offset_x,
                        offset_y,
                    )

                else:
                    continue

                drawn_items += 1

            except (TypeError, ValueError, IndexError):
                # One malformed command should not prevent the
                # remaining vector paths from being rendered.
                continue

        if drawn_items == 0:
            return False

        shape.finish(
            color=cls._normalise_color(
                drawing.get("color")
            ),
            fill=cls._normalise_color(
                drawing.get("fill")
            ),
            dashes=cls._normalise_dashes(
                drawing.get("dashes")
            ),
            even_odd=bool(
                drawing.get("even_odd", False)
            ),
            closePath=bool(
                drawing.get("closePath", False)
            ),
            lineJoin=cls._safe_number(
                drawing.get("lineJoin"),
                default=0.0,
            ),
            lineCap=cls._normalise_line_cap(
                drawing.get("lineCap")
            ),
            width=max(
                cls._safe_number(
                    drawing.get("width"),
                    default=1.0,
                ),
                0.0,
            ),
            stroke_opacity=cls._safe_opacity(
                drawing.get("stroke_opacity")
            ),
            fill_opacity=cls._safe_opacity(
                drawing.get("fill_opacity")
            ),
        )

        shape.commit()

        return True

    @staticmethod
    def _draw_line(
        shape,
        item: tuple,
        offset_x: float,
        offset_y: float,
    ) -> None:
        start = VectorGraphicRegionRenderer._translate_point(
            item[1],
            offset_x,
            offset_y,
        )

        end = VectorGraphicRegionRenderer._translate_point(
            item[2],
            offset_x,
            offset_y,
        )

        shape.draw_line(
            start,
            end,
        )

    @staticmethod
    def _draw_curve(
        shape,
        item: tuple,
        offset_x: float,
        offset_y: float,
    ) -> None:
        point_1 = (
            VectorGraphicRegionRenderer
            ._translate_point(
                item[1],
                offset_x,
                offset_y,
            )
        )

        point_2 = (
            VectorGraphicRegionRenderer
            ._translate_point(
                item[2],
                offset_x,
                offset_y,
            )
        )

        point_3 = (
            VectorGraphicRegionRenderer
            ._translate_point(
                item[3],
                offset_x,
                offset_y,
            )
        )

        point_4 = (
            VectorGraphicRegionRenderer
            ._translate_point(
                item[4],
                offset_x,
                offset_y,
            )
        )

        shape.draw_bezier(
            point_1,
            point_2,
            point_3,
            point_4,
        )

    @staticmethod
    def _draw_rectangle(
        shape,
        item: tuple,
        offset_x: float,
        offset_y: float,
    ) -> None:
        rectangle = item[1]

        translated_rectangle = pymupdf.Rect(
            rectangle.x0 + offset_x,
            rectangle.y0 + offset_y,
            rectangle.x1 + offset_x,
            rectangle.y1 + offset_y,
        )

        shape.draw_rect(
            translated_rectangle
        )

    @staticmethod
    def _draw_quad(
        shape,
        item: tuple,
        offset_x: float,
        offset_y: float,
    ) -> None:
        quad = item[1]

        translated_quad = pymupdf.Quad(
            VectorGraphicRegionRenderer._translate_point(
                quad.ul,
                offset_x,
                offset_y,
            ),
            VectorGraphicRegionRenderer._translate_point(
                quad.ur,
                offset_x,
                offset_y,
            ),
            VectorGraphicRegionRenderer._translate_point(
                quad.ll,
                offset_x,
                offset_y,
            ),
            VectorGraphicRegionRenderer._translate_point(
                quad.lr,
                offset_x,
                offset_y,
            ),
        )

        shape.draw_quad(
            translated_quad
        )

    @staticmethod
    def _translate_point(
        point: Any,
        offset_x: float,
        offset_y: float,
    ) -> pymupdf.Point:
        return pymupdf.Point(
            float(point.x) + offset_x,
            float(point.y) + offset_y,
        )

    @staticmethod
    def _normalise_color(
        color: Any,
    ) -> tuple[float, ...] | None:
        if color is None:
            return None

        if not isinstance(
            color,
            (tuple, list),
        ):
            return None

        try:
            return tuple(
                max(
                    0.0,
                    min(
                        float(component),
                        1.0,
                    ),
                )
                for component in color
            )

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalise_dashes(
        dashes: Any,
    ) -> str | None:
        if dashes in (
            None,
            "",
            "[] 0",
        ):
            return None

        return str(dashes)

    @staticmethod
    def _normalise_line_cap(
        line_cap: Any,
    ) -> int:
        if isinstance(
            line_cap,
            (tuple, list),
        ):
            values = [
                int(value)
                for value in line_cap
                if value is not None
            ]

            return max(
                values,
                default=0,
            )

        try:
            return int(line_cap or 0)

        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_number(
        value: Any,
        default: float,
    ) -> float:
        try:
            if value is None:
                return default

            return float(value)

        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_opacity(
        value: Any,
    ) -> float:
        try:
            if value is None:
                return 1.0

            return max(
                0.0,
                min(
                    float(value),
                    1.0,
                ),
            )

        except (TypeError, ValueError):
            return 1.0