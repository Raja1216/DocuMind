from __future__ import annotations

from src.models.vector_graphic import VectorGraphic


class VectorGraphicMapper:
    """
    Maps a PyMuPDF drawing dictionary into the DocuMind
    VectorGraphic model.
    """

    @staticmethod
    def map(
        drawing_data: dict,
        page_number: int,
        sequence_number: int,
    ) -> VectorGraphic | None:

        drawing_rect = drawing_data.get(
            "rect"
        )

        if drawing_rect is None:
            return None

        return VectorGraphic(
            page_number=page_number,

            left=float(drawing_rect.x0),
            top=float(drawing_rect.y0),
            right=float(drawing_rect.x1),
            bottom=float(drawing_rect.y1),

            sequence_number=sequence_number,

            drawing_type=(
                VectorGraphicMapper
                ._detect_drawing_type(
                    drawing_data
                )
            ),

            stroke_color=(
                VectorGraphicMapper._rgb_to_hex(
                    drawing_data.get("color")
                )
            ),

            fill_color=(
                VectorGraphicMapper._rgb_to_hex(
                    drawing_data.get("fill")
                )
            ),

            stroke_width=VectorGraphicMapper._safe_float(
                drawing_data.get("width"),
            ),
            
            fill_opacity=VectorGraphicMapper._safe_float(
                drawing_data.get("fill_opacity"),
                1.0,
            ),
            
            stroke_opacity=VectorGraphicMapper._safe_float(
                drawing_data.get("stroke_opacity"),
                1.0,
            ),

            even_odd_fill=bool(
                drawing_data.get(
                    "even_odd",
                    False,
                )
            ),

            close_path=bool(
                drawing_data.get(
                    "closePath",
                    False,
                )
            ),

            line_cap=(
                VectorGraphicMapper
                ._safe_integer(
                    drawing_data.get(
                        "lineCap"
                    )
                )
            ),

            line_join=(
                VectorGraphicMapper
                ._safe_integer(
                    drawing_data.get(
                        "lineJoin"
                    )
                )
            ),

            dash_pattern=(
                str(drawing_data.get("dashes"))
                if drawing_data.get("dashes")
                is not None
                else None
            ),

            items=list(
                drawing_data.get(
                    "items",
                    []
                )
            ),
            source_drawing=drawing_data,
        )

    @staticmethod
    def _safe_float(
        value,
        default: float = 0.0,
    ) -> float:
        """
        Convert a value to float.

        Returns the default when the value is None
        or cannot be converted.
        """

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _detect_drawing_type(
        drawing_data: dict,
    ) -> str:
        """
        Classify the drawing using its PyMuPDF path items.
        """

        items = drawing_data.get(
            "items",
            []
        )

        operation_types = {
            item[0]
            for item in items
            if item
        }

        if not operation_types:
            return "unknown"

        if operation_types == {"re"}:
            return "rectangle"

        if operation_types <= {"l"}:
            return "line"

        if "c" in operation_types:
            return "curve"

        if "qu" in operation_types:
            return "quadrilateral"

        return "compound"

    @staticmethod
    def _rgb_to_hex(
        color,
    ) -> str | None:
        """
        Convert a PyMuPDF normalized RGB tuple to hex.
        """

        if color is None:
            return None

        if len(color) < 3:
            return None

        red = VectorGraphicMapper._component_to_int(
            color[0]
        )

        green = VectorGraphicMapper._component_to_int(
            color[1]
        )

        blue = VectorGraphicMapper._component_to_int(
            color[2]
        )

        return (
            f"#{red:02X}"
            f"{green:02X}"
            f"{blue:02X}"
        )

    @staticmethod
    def _component_to_int(
        value: float,
    ) -> int:
        value = min(
            max(float(value), 0.0),
            1.0,
        )

        return int(
            round(value * 255)
        )

    @staticmethod
    def _safe_integer(
        value,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(value, (list, tuple)):
            if not value:
                return None

            value = value[0]

        try:
            return int(value)
        except (TypeError, ValueError):
            return None