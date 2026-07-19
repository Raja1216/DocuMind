from __future__ import annotations

import math

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


class WordNumberingManager:
    """
    Creates valid Word bullet and decimal-numbering
    definitions.

    Important WordprocessingML ordering rule:

        abstractNum*
        num*

    All abstract definitions must appear before all numbering
    instances. Interleaving them can cause Microsoft Word to
    repair the document and connect unrelated lists.
    """

    BULLET_CHARACTER = "•"

    DEFAULT_LEFT_TWIPS = 720
    DEFAULT_HANGING_TWIPS = 360

    def __init__(
        self,
        word_document,
    ) -> None:
        self.numbering_element = (
            word_document
            .part
            .numbering_part
            .element
        )

        # One abstract definition can be reused by multiple
        # independent list sequences.
        self._abstract_cache: dict[
            tuple[str, str, int],
            int,
        ] = {}

    def create_list(
        self,
        list_type: str,
        start_at: int = 1,
        marker_font_name: str = "Arial",
        marker_font_size: float = 11.0,
    ) -> int:
        """
        Create an independent list sequence.

        A new numId is created for every separate list. This
        guarantees that numbered lists restart independently.
        """

        if list_type not in {
            "bullet",
            "number",
        }:
            raise ValueError(
                f"Unsupported list type: {list_type}"
            )

        marker_half_points = (
            self._to_half_points(
                marker_font_size
            )
        )

        cache_key = (
            list_type,
            marker_font_name,
            marker_half_points,
        )

        abstract_number_id = (
            self._abstract_cache.get(
                cache_key
            )
        )

        if abstract_number_id is None:
            abstract_number_id = (
                self._next_abstract_number_id()
            )

            abstract_number = (
                self._create_abstract_number(
                    abstract_number_id=(
                        abstract_number_id
                    ),
                    list_type=list_type,
                    marker_font_name=(
                        marker_font_name
                    ),
                    marker_half_points=(
                        marker_half_points
                    ),
                )
            )

            self._insert_abstract_number(
                abstract_number
            )

            self._abstract_cache[
                cache_key
            ] = abstract_number_id

        number_id = (
            self._next_number_id()
        )

        number_instance = (
            self._create_number_instance(
                number_id=number_id,
                abstract_number_id=(
                    abstract_number_id
                ),
                list_type=list_type,
                start_at=start_at,
            )
        )

        # num elements belong after all abstractNum elements.
        self.numbering_element.append(
            number_instance
        )

        return number_id

    def _insert_abstract_number(
        self,
        abstract_number,
    ) -> None:
        """
        Insert abstractNum before the first num element.

        Appending an abstractNum after num elements produces an
        invalid numbering.xml child order.
        """

        first_number = (
            self.numbering_element.find(
                qn("w:num")
            )
        )

        if first_number is None:
            self.numbering_element.append(
                abstract_number
            )
            return

        number_index = (
            self.numbering_element.index(
                first_number
            )
        )

        self.numbering_element.insert(
            number_index,
            abstract_number,
        )

    def _create_abstract_number(
        self,
        abstract_number_id: int,
        list_type: str,
        marker_font_name: str,
        marker_half_points: int,
    ):
        abstract_number = OxmlElement(
            "w:abstractNum"
        )

        abstract_number.set(
            qn("w:abstractNumId"),
            str(abstract_number_id),
        )

        multi_level_type = OxmlElement(
            "w:multiLevelType"
        )

        multi_level_type.set(
            qn("w:val"),
            "singleLevel",
        )

        abstract_number.append(
            multi_level_type
        )

        level = OxmlElement(
            "w:lvl"
        )

        level.set(
            qn("w:ilvl"),
            "0",
        )

        start = OxmlElement(
            "w:start"
        )

        start.set(
            qn("w:val"),
            "1",
        )

        level.append(start)

        number_format = OxmlElement(
            "w:numFmt"
        )

        number_format.set(
            qn("w:val"),
            (
                "bullet"
                if list_type == "bullet"
                else "decimal"
            ),
        )

        level.append(
            number_format
        )

        level_text = OxmlElement(
            "w:lvlText"
        )

        level_text.set(
            qn("w:val"),
            (
                self.BULLET_CHARACTER
                if list_type == "bullet"
                else "%1."
            ),
        )

        level.append(
            level_text
        )

        level_justification = OxmlElement(
            "w:lvlJc"
        )

        level_justification.set(
            qn("w:val"),
            (
                "left"
                if list_type == "bullet"
                else "right"
            ),
        )

        level.append(
            level_justification
        )

        suffix = OxmlElement(
            "w:suff"
        )

        suffix.set(
            qn("w:val"),
            "tab",
        )

        level.append(
            suffix
        )

        paragraph_properties = OxmlElement(
            "w:pPr"
        )

        indentation = OxmlElement(
            "w:ind"
        )

        indentation.set(
            qn("w:left"),
            str(
                self.DEFAULT_LEFT_TWIPS
            ),
        )

        indentation.set(
            qn("w:hanging"),
            str(
                self.DEFAULT_HANGING_TWIPS
            ),
        )

        paragraph_properties.append(
            indentation
        )

        level.append(
            paragraph_properties
        )

        # Explicitly style both bullet and number markers.
        # Otherwise Word may render labels using the default
        # 11-point Normal style.
        run_properties = OxmlElement(
            "w:rPr"
        )

        fonts = OxmlElement(
            "w:rFonts"
        )

        for font_attribute in (
            "w:ascii",
            "w:hAnsi",
            "w:eastAsia",
            "w:cs",
        ):
            fonts.set(
                qn(font_attribute),
                marker_font_name,
            )

        run_properties.append(
            fonts
        )

        font_size = OxmlElement(
            "w:sz"
        )

        font_size.set(
            qn("w:val"),
            str(marker_half_points),
        )

        run_properties.append(
            font_size
        )

        complex_font_size = OxmlElement(
            "w:szCs"
        )

        complex_font_size.set(
            qn("w:val"),
            str(marker_half_points),
        )

        run_properties.append(
            complex_font_size
        )

        level.append(
            run_properties
        )

        abstract_number.append(
            level
        )

        return abstract_number

    @staticmethod
    def _create_number_instance(
        number_id: int,
        abstract_number_id: int,
        list_type: str,
        start_at: int,
    ):
        number = OxmlElement(
            "w:num"
        )

        number.set(
            qn("w:numId"),
            str(number_id),
        )

        abstract_reference = OxmlElement(
            "w:abstractNumId"
        )

        abstract_reference.set(
            qn("w:val"),
            str(abstract_number_id),
        )

        number.append(
            abstract_reference
        )

        if list_type == "number":
            level_override = OxmlElement(
                "w:lvlOverride"
            )

            level_override.set(
                qn("w:ilvl"),
                "0",
            )

            start_override = OxmlElement(
                "w:startOverride"
            )

            start_override.set(
                qn("w:val"),
                str(
                    max(
                        int(start_at),
                        1,
                    )
                ),
            )

            level_override.append(
                start_override
            )

            number.append(
                level_override
            )

        return number

    def _next_abstract_number_id(
        self,
    ) -> int:
        identifiers = [
            int(
                element.get(
                    qn("w:abstractNumId")
                )
            )
            for element
            in self.numbering_element.findall(
                qn("w:abstractNum")
            )
            if element.get(
                qn("w:abstractNumId")
            ) is not None
        ]

        return (
            max(
                identifiers,
                default=-1,
            )
            + 1
        )

    def _next_number_id(
        self,
    ) -> int:
        identifiers = [
            int(
                element.get(
                    qn("w:numId")
                )
            )
            for element
            in self.numbering_element.findall(
                qn("w:num")
            )
            if element.get(
                qn("w:numId")
            ) is not None
        ]

        return (
            max(
                identifiers,
                default=0,
            )
            + 1
        )

    @staticmethod
    def _to_half_points(
        point_size: float,
    ) -> int:
        """
        Word stores font size using half-point integers.
        """

        value = max(
            float(point_size),
            0.5,
        )

        return max(
            int(
                math.floor(
                    value * 2.0 + 0.5
                )
            ),
            1,
        )