from __future__ import annotations


class VectorGraphicExtractor:
    """
    Extracts paintable vector drawing paths from one
    PyMuPDF page while preserving active clipping paths.
    """

    PAINT_TYPES = {
        "f",
        "s",
        "fs",
    }

    @classmethod
    def extract(
        cls,
        pdf_page,
    ) -> list[dict]:
        """
        Return paintable PyMuPDF drawing dictionaries.

        Clip and group dictionaries are not returned as
        standalone graphics. Instead, active clip paths are
        attached to every drawing they affect.
        """

        drawings = pdf_page.get_drawings(
            extended=True
        )

        if not drawings:
            return []

        active_clips: list[
            tuple[int, dict]
        ] = []

        extracted_drawings: list[dict] = []

        for drawing in drawings:
            level = cls._safe_level(
                drawing.get("level")
            )

            # Any entry at the same or a lower level ends the
            # previous clip scope at that level.
            active_clips = [
                (
                    clip_level,
                    clip_drawing,
                )
                for (
                    clip_level,
                    clip_drawing,
                ) in active_clips
                if clip_level < level
            ]

            drawing_type = str(
                drawing.get("type") or ""
            ).lower()

            if drawing_type == "clip":
                active_clips.append(
                    (
                        level,
                        drawing,
                    )
                )

                continue

            if drawing_type == "group":
                # Groups will be handled separately later for
                # opacity and blend-mode support.
                continue

            if (
                drawing_type
                not in cls.PAINT_TYPES
            ):
                continue

            normalized_drawing = dict(
                drawing
            )

            normalized_drawing[
                "_documind_active_clips"
            ] = [
                clip_drawing
                for (
                    _,
                    clip_drawing,
                ) in active_clips
            ]

            extracted_drawings.append(
                normalized_drawing
            )

        return extracted_drawings

    @staticmethod
    def _safe_level(
        value,
    ) -> int:
        try:
            if value is None:
                return 0

            return int(value)

        except (TypeError, ValueError):
            return 0