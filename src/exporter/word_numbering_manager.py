from __future__ import annotations

import math

from collections import Counter
from dataclasses import dataclass
from statistics import median

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from src.models.list_item import (
    ListMarkerKind,
)
from src.models.list_sequence import (
    ListSequence,
)


@dataclass(
    frozen=True,
    slots=True,
)
class WordListLevelDefinition:
    """
    Normalized Word numbering definition for one list level.
    """

    level: int

    number_format: str
    level_text: str
    justification: str

    left_twips: int
    hanging_twips: int

    marker_font_name: str
    marker_half_points: int


class WordNumberingManager:
    """
    Creates valid single-level and multilevel Word lists.

    Important numbering.xml child order:

        abstractNum*
        num*

    Every abstractNum must appear before every num element.
    """

    MAXIMUM_LEVEL = 8

    DEFAULT_BULLET_CHARACTER = "•"

    BULLET_CHARACTERS_BY_LEVEL = (
        "•",
        "◦",
        "▪",
        "▫",
        "●",
        "○",
        "■",
        "□",
        "‣",
    )
    
    LEGACY_SYMBOL_FONT_TOKENS = (
        "symbol",
        "wingdings",
        "webdings",
        "zapfdingbats",
        "dingbats",
    )
    
    DEFAULT_LEFT_TWIPS = 720
    DEFAULT_HANGING_TWIPS = 360

    LEVEL_INDENT_INCREMENT_TWIPS = 360

    NUMBER_KIND_BY_LEVEL = (
        ListMarkerKind.DECIMAL,
        ListMarkerKind.LOWER_ALPHA,
        ListMarkerKind.LOWER_ROMAN,
        ListMarkerKind.UPPER_ALPHA,
        ListMarkerKind.UPPER_ROMAN,
    )

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

        # Abstract definitions can be shared when every level
        # has the same style.
        self._abstract_cache: dict[
            tuple[
                tuple[
                    str,
                    str,
                    str,
                    int,
                    int,
                    str,
                    int,
                ],
                ...,
            ],
            int,
        ] = {}

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def create_list(
        self,
        list_type: str,
        start_at: int = 1,
        marker_font_name: str = "Arial",
        marker_font_size: float = 11.0,
    ) -> int:
        """
        Backward-compatible single-level list creation.

        Existing exporter code can continue calling this method
        until sequence integration is completed.
        """

        if list_type not in {
            "bullet",
            "number",
        }:
            raise ValueError(
                f"Unsupported list type: {list_type}"
            )
        marker_font_name = (
            self._normalize_marker_font(
                list_type=list_type,
                marker_font_name=(
                    marker_font_name
                ),
            )
        )
        marker_half_points = (
            self._to_half_points(
                marker_font_size
            )
        )

        if list_type == "bullet":
            definition = (
                WordListLevelDefinition(
                    level=0,
                    number_format="bullet",
                    level_text=(
                        self.DEFAULT_BULLET_CHARACTER
                    ),
                    justification="left",
                    left_twips=(
                        self.DEFAULT_LEFT_TWIPS
                    ),
                    hanging_twips=(
                        self.DEFAULT_HANGING_TWIPS
                    ),
                    marker_font_name=(
                        marker_font_name
                    ),
                    marker_half_points=(
                        marker_half_points
                    ),
                )
            )

            start_overrides = {}

        else:
            definition = (
                WordListLevelDefinition(
                    level=0,
                    number_format="decimal",
                    level_text="%1.",
                    justification="right",
                    left_twips=(
                        self.DEFAULT_LEFT_TWIPS
                    ),
                    hanging_twips=(
                        self.DEFAULT_HANGING_TWIPS
                    ),
                    marker_font_name=(
                        marker_font_name
                    ),
                    marker_half_points=(
                        marker_half_points
                    ),
                )
            )

            start_overrides = {
                0: max(
                    int(start_at),
                    1,
                )
            }

        return self._create_numbering_instance(
            level_definitions=[
                definition
            ],
            start_overrides=(
                start_overrides
            ),
        )

    def create_sequence(
        self,
        sequence: ListSequence,
        marker_font_name: str = "Arial",
        marker_font_size: float = 11.0,
    ) -> int:
        """
        Create one genuine multilevel Word numbering sequence.
    
        Every logical ListSequence receives its own numId, while
        compatible sequences may reuse the same abstractNum.
        """
    
        if sequence.list_type not in {
            "bullet",
            "number",
        }:
            raise ValueError(
                (
                    "Unsupported sequence list type: "
                    f"{sequence.list_type}"
                )
            )
    
        # This must be outside the error condition and before
        # level definitions are created.
        marker_font_name = (
            self._normalize_marker_font(
                list_type=(
                    sequence.list_type
                ),
                marker_font_name=(
                    marker_font_name
                ),
            )
        )
    
        level_definitions = (
            self._build_sequence_level_definitions(
                sequence=sequence,
                marker_font_name=(
                    marker_font_name
                ),
                marker_font_size=(
                    marker_font_size
                ),
            )
        )
    
        start_overrides = (
            self._build_start_overrides(
                sequence
            )
        )
    
        return self._create_numbering_instance(
            level_definitions=(
                level_definitions
            ),
            start_overrides=(
                start_overrides
            ),
        )

    # ---------------------------------------------------------
    # Sequence definition building
    # ---------------------------------------------------------

    def _build_sequence_level_definitions(
        self,
        sequence: ListSequence,
        marker_font_name: str,
        marker_font_size: float,
    ) -> list[WordListLevelDefinition]:
        maximum_level = min(
            max(
                int(
                    sequence.maximum_level
                ),
                0,
            ),
            self.MAXIMUM_LEVEL,
        )

        marker_half_points = (
            self._to_half_points(
                marker_font_size
            )
        )

        definitions: list[
            WordListLevelDefinition
        ] = []

        for level in range(
            maximum_level + 1
        ):
            level_items = [
                item
                for item in sequence.items
                if item.level == level
            ]

            marker_kind = (
                self._resolve_level_marker_kind(
                    list_type=sequence.list_type,
                    level=level,
                    level_items=level_items,
                )
            )

            representative_marker = (
                str(
                    level_items[0].marker
                )
                if level_items
                else ""
            )

            number_format = (
                self._resolve_number_format(
                    list_type=sequence.list_type,
                    marker_kind=marker_kind,
                )
            )

            level_text = (
                self._resolve_level_text(
                    list_type=sequence.list_type,
                    marker_kind=marker_kind,
                    marker=representative_marker,
                    level=level,
                )
            )

            (
                left_twips,
                hanging_twips,
            ) = self._resolve_level_indentation(
                sequence=sequence,
                level=level,
                level_items=level_items,
            )

            definitions.append(
                WordListLevelDefinition(
                    level=level,
                    number_format=(
                        number_format
                    ),
                    level_text=level_text,
                    justification=(
                        "left"
                        if (
                            sequence.list_type
                            == "bullet"
                        )
                        else "right"
                    ),
                    left_twips=left_twips,
                    hanging_twips=(
                        hanging_twips
                    ),
                    marker_font_name=(
                        marker_font_name
                    ),
                    marker_half_points=(
                        marker_half_points
                    ),
                )
            )

        return definitions

    def _resolve_level_marker_kind(
        self,
        list_type: str,
        level: int,
        level_items,
    ) -> ListMarkerKind:
        if level_items:
            valid_kinds = [
                item.marker_kind
                for item in level_items
                if (
                    item.marker_kind
                    != ListMarkerKind.UNKNOWN
                )
            ]

            if valid_kinds:
                return (
                    Counter(
                        valid_kinds
                    )
                    .most_common(1)[0][0]
                )

        if list_type == "bullet":
            return ListMarkerKind.BULLET

        return self.NUMBER_KIND_BY_LEVEL[
            level
            % len(
                self.NUMBER_KIND_BY_LEVEL
            )
        ]

    @staticmethod
    def _resolve_number_format(
        list_type: str,
        marker_kind: ListMarkerKind,
    ) -> str:
        if list_type == "bullet":
            return "bullet"

        format_map = {
            ListMarkerKind.DECIMAL: (
                "decimal"
            ),

            ListMarkerKind.MULTILEVEL_DECIMAL: (
                "decimal"
            ),

            ListMarkerKind.LOWER_ALPHA: (
                "lowerLetter"
            ),

            ListMarkerKind.UPPER_ALPHA: (
                "upperLetter"
            ),

            ListMarkerKind.LOWER_ROMAN: (
                "lowerRoman"
            ),

            ListMarkerKind.UPPER_ROMAN: (
                "upperRoman"
            ),
        }

        return format_map.get(
            marker_kind,
            "decimal",
        )

    def _resolve_level_text(
        self,
        list_type: str,
        marker_kind: ListMarkerKind,
        marker: str,
        level: int,
    ) -> str:
        if list_type == "bullet":
            normalized_marker = (
                marker.strip()
            )

            if (
                normalized_marker
                and len(
                    normalized_marker
                )
                == 1
            ):
                return normalized_marker

            return (
                self
                .BULLET_CHARACTERS_BY_LEVEL[
                    level
                    % len(
                        self
                        .BULLET_CHARACTERS_BY_LEVEL
                    )
                ]
            )

        if (
            marker_kind
            == ListMarkerKind
            .MULTILEVEL_DECIMAL
        ):
            placeholder = ".".join(
                f"%{index}"
                for index in range(
                    1,
                    level + 2,
                )
            )

        else:
            placeholder = (
                f"%{level + 1}"
            )

        return self._apply_marker_punctuation(
            placeholder=placeholder,
            marker=marker,
        )

    @staticmethod
    def _apply_marker_punctuation(
        placeholder: str,
        marker: str,
    ) -> str:
        normalized = marker.strip()

        if (
            normalized.startswith("(")
            and normalized.endswith(")")
        ):
            return (
                f"({placeholder})"
            )

        if normalized.endswith(")"):
            return (
                f"{placeholder})"
            )

        if normalized.endswith("."):
            return (
                f"{placeholder}."
            )

        # Word lists should still have a stable visible suffix
        # when the PDF marker has no recognized punctuation.
        return (
            f"{placeholder}."
        )

    def _resolve_level_indentation(
        self,
        sequence: ListSequence,
        level: int,
        level_items,
    ) -> tuple[int, int]:
        minimum_left_twips = (
            self.DEFAULT_LEFT_TWIPS
            + (
                level
                * self
                .LEVEL_INDENT_INCREMENT_TWIPS
            )
        )

        measured_indents = []

        for item in level_items:
            relative_indent = max(
                float(
                    item.indent
                )
                - float(
                    sequence.container_left
                ),
                0.0,
            )

            measured_indents.append(
                relative_indent
            )

        if measured_indents:
            measured_left_twips = (
                self._points_to_twips(
                    median(
                        measured_indents
                    )
                )
            )

            left_twips = max(
                measured_left_twips,
                minimum_left_twips,
            )

        else:
            left_twips = (
                minimum_left_twips
            )

        hanging_twips = min(
            self.DEFAULT_HANGING_TWIPS,
            max(
                left_twips // 2,
                240,
            ),
        )

        return (
            left_twips,
            hanging_twips,
        )

    # ---------------------------------------------------------
    # Numbering starts
    # ---------------------------------------------------------

    def _build_start_overrides(
        self,
        sequence: ListSequence,
    ) -> dict[int, int]:
        if sequence.list_type != "number":
            return {}

        overrides: dict[
            int,
            int,
        ] = {
            0: max(
                int(
                    sequence.start_at
                ),
                1,
            )
        }

        encountered_levels = {
            0
        }

        for item in sequence.items:
            level = min(
                max(
                    int(
                        item.level
                    ),
                    0,
                ),
                self.MAXIMUM_LEVEL,
            )

            if level in encountered_levels:
                continue

            start_value = None

            if (
                item.multilevel_value
                is not None
                and len(
                    item.multilevel_value
                )
                > level
            ):
                start_value = (
                    item.multilevel_value[
                        level
                    ]
                )

            elif item.numeric_value is not None:
                start_value = (
                    item.numeric_value
                )

            if (
                start_value is not None
                and int(
                    start_value
                )
                > 1
            ):
                overrides[
                    level
                ] = int(
                    start_value
                )

            encountered_levels.add(
                level
            )

        return overrides

    # ---------------------------------------------------------
    # XML creation
    # ---------------------------------------------------------

    def _create_numbering_instance(
        self,
        level_definitions: list[
            WordListLevelDefinition
        ],
        start_overrides: dict[
            int,
            int,
        ],
    ) -> int:
        cache_key = tuple(
            (
                definition.number_format,
                definition.level_text,
                definition.justification,
                definition.left_twips,
                definition.hanging_twips,
                definition.marker_font_name,
                definition.marker_half_points,
            )
            for definition
            in level_definitions
        )

        abstract_number_id = (
            self._abstract_cache.get(
                cache_key
            )
        )

        if abstract_number_id is None:
            abstract_number_id = (
                self
                ._next_abstract_number_id()
            )

            abstract_number = (
                self._create_abstract_number(
                    abstract_number_id=(
                        abstract_number_id
                    ),
                    level_definitions=(
                        level_definitions
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
                start_overrides=(
                    start_overrides
                ),
            )
        )

        self.numbering_element.append(
            number_instance
        )

        return number_id

    def _create_abstract_number(
        self,
        abstract_number_id: int,
        level_definitions: list[
            WordListLevelDefinition
        ],
    ):
        abstract_number = OxmlElement(
            "w:abstractNum"
        )

        abstract_number.set(
            qn(
                "w:abstractNumId"
            ),
            str(
                abstract_number_id
            ),
        )

        multi_level_type = OxmlElement(
            "w:multiLevelType"
        )

        multi_level_type.set(
            qn("w:val"),
            (
                "multilevel"
                if len(
                    level_definitions
                )
                > 1
                else "singleLevel"
            ),
        )

        abstract_number.append(
            multi_level_type
        )

        for definition in (
            level_definitions
        ):
            abstract_number.append(
                self._create_level(
                    definition
                )
            )

        return abstract_number

    def _create_level(
        self,
        definition: WordListLevelDefinition,
    ):
        level = OxmlElement(
            "w:lvl"
        )

        level.set(
            qn("w:ilvl"),
            str(
                definition.level
            ),
        )

        start = OxmlElement(
            "w:start"
        )

        start.set(
            qn("w:val"),
            "1",
        )

        level.append(
            start
        )

        number_format = OxmlElement(
            "w:numFmt"
        )

        number_format.set(
            qn("w:val"),
            definition.number_format,
        )

        level.append(
            number_format
        )

        level_text = OxmlElement(
            "w:lvlText"
        )

        level_text.set(
            qn("w:val"),
            definition.level_text,
        )

        level.append(
            level_text
        )

        level_justification = (
            OxmlElement(
                "w:lvlJc"
            )
        )

        level_justification.set(
            qn("w:val"),
            definition.justification,
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

        paragraph_properties = (
            OxmlElement(
                "w:pPr"
            )
        )

        indentation = OxmlElement(
            "w:ind"
        )

        indentation.set(
            qn("w:left"),
            str(
                definition.left_twips
            ),
        )

        indentation.set(
            qn("w:hanging"),
            str(
                definition.hanging_twips
            ),
        )

        paragraph_properties.append(
            indentation
        )

        level.append(
            paragraph_properties
        )

        run_properties = OxmlElement(
            "w:rPr"
        )

        fonts = OxmlElement(
            "w:rFonts"
        )

        for attribute_name in (
            "w:ascii",
            "w:hAnsi",
            "w:eastAsia",
            "w:cs",
        ):
            fonts.set(
                qn(attribute_name),
                definition.marker_font_name,
            )

        run_properties.append(
            fonts
        )

        font_size = OxmlElement(
            "w:sz"
        )

        font_size.set(
            qn("w:val"),
            str(
                definition
                .marker_half_points
            ),
        )

        run_properties.append(
            font_size
        )

        complex_font_size = (
            OxmlElement(
                "w:szCs"
            )
        )

        complex_font_size.set(
            qn("w:val"),
            str(
                definition
                .marker_half_points
            ),
        )

        run_properties.append(
            complex_font_size
        )

        level.append(
            run_properties
        )

        return level

    @staticmethod
    def _create_number_instance(
        number_id: int,
        abstract_number_id: int,
        start_overrides: dict[
            int,
            int,
        ],
    ):
        number = OxmlElement(
            "w:num"
        )

        number.set(
            qn("w:numId"),
            str(
                number_id
            ),
        )

        abstract_reference = (
            OxmlElement(
                "w:abstractNumId"
            )
        )

        abstract_reference.set(
            qn("w:val"),
            str(
                abstract_number_id
            ),
        )

        number.append(
            abstract_reference
        )

        for (
            level,
            start_at,
        ) in sorted(
            start_overrides.items()
        ):
            level_override = (
                OxmlElement(
                    "w:lvlOverride"
                )
            )

            level_override.set(
                qn("w:ilvl"),
                str(
                    level
                ),
            )

            start_override = (
                OxmlElement(
                    "w:startOverride"
                )
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

    # ---------------------------------------------------------
    # XML ordering and identifiers
    # ---------------------------------------------------------

    def _insert_abstract_number(
        self,
        abstract_number,
    ) -> None:
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

    def _next_abstract_number_id(
        self,
    ) -> int:
        identifiers = [
            int(
                element.get(
                    qn(
                        "w:abstractNumId"
                    )
                )
            )
            for element
            in (
                self.numbering_element
                .findall(
                    qn(
                        "w:abstractNum"
                    )
                )
            )
            if element.get(
                qn(
                    "w:abstractNumId"
                )
            )
            is not None
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
            )
            is not None
        ]

        return (
            max(
                identifiers,
                default=0,
            )
            + 1
        )

    @classmethod
    def _normalize_marker_font(
        cls,
        list_type: str,
        marker_font_name: str,
    ) -> str:
        """
        Prevent a Unicode bullet such as U+2022 from being rendered
        using a legacy Symbol/Wingdings character map.
        """

        normalized_name = str(
            marker_font_name
            or "Arial"
        ).strip()

        if not normalized_name:
            normalized_name = "Arial"

        if list_type != "bullet":
            return normalized_name

        lower_name = (
            normalized_name.casefold()
        )

        if any(
            token in lower_name

            for token
            in cls.LEGACY_SYMBOL_FONT_TOKENS
        ):
            return "Arial"

        return normalized_name

    # ---------------------------------------------------------
    # Unit helpers
    # ---------------------------------------------------------

    @staticmethod
    def _to_half_points(
        point_size: float,
    ) -> int:
        value = max(
            float(
                point_size
            ),
            0.5,
        )

        return max(
            int(
                math.floor(
                    value * 2.0
                    + 0.5
                )
            ),
            1,
        )

    @staticmethod
    def _points_to_twips(
        point_value: float,
    ) -> int:
        return max(
            int(
                round(
                    float(
                        point_value
                    )
                    * 20.0
                )
            ),
            0,
        )