from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableTableDisposition(
    str,
    Enum,
):
    """
    Final rendering strategy for one normalized table.
    """

    EDITABLE = "editable"

    VISUAL_FALLBACK = "visual_fallback"

    SKIP = "skip"


class EditableCellHorizontalAlignment(
    str,
    Enum,
):
    """
    Horizontal text alignment inside a Word table cell.
    """

    LEFT = "left"

    CENTER = "center"

    RIGHT = "right"

    JUSTIFY = "justify"

    UNKNOWN = "unknown"


class EditableCellVerticalAlignment(
    str,
    Enum,
):
    """
    Vertical text alignment inside a Word table cell.
    """

    TOP = "top"

    CENTER = "center"

    BOTTOM = "bottom"

    UNKNOWN = "unknown"


class EditableBorderLineStyle(
    str,
    Enum,
):
    """
    Border styles that can be represented reliably in Word.
    """

    NONE = "none"

    SINGLE = "single"

    DOUBLE = "double"

    DASHED = "dashed"

    DOTTED = "dotted"


@dataclass(slots=True)
class EditableTableBorder:
    """
    One normalized border edge.

    width is measured in PDF/Word points.
    color uses a six-digit RGB hex string without '#'.
    """

    style: EditableBorderLineStyle = (
        EditableBorderLineStyle.SINGLE
    )

    color: str = "B7B7B7"

    width: float = 0.5

    confidence: float = 0.0

    def __post_init__(
        self,
    ) -> None:
        self.color = self.normalize_color(
            self.color
        )

        self.width = max(
            float(
                self.width
            ),
            0.0,
        )

        self.confidence = self.clamp_confidence(
            self.confidence
        )

        if self.style == EditableBorderLineStyle.NONE:
            self.width = 0.0

    @staticmethod
    def normalize_color(
        color: str | None,
    ) -> str:
        normalized = str(
            color
            or "B7B7B7"
        ).strip().lstrip(
            "#"
        ).upper()

        if re_full_hex(
            normalized
        ):
            return normalized

        return "B7B7B7"

    @staticmethod
    def clamp_confidence(
        confidence: float,
    ) -> float:
        return max(
            0.0,
            min(
                float(
                    confidence
                ),
                1.0,
            ),
        )


@dataclass(slots=True)
class EditableTableCellBorders:
    """
    Independent border styles for all four cell edges.
    """

    top: EditableTableBorder = field(
        default_factory=EditableTableBorder
    )

    right: EditableTableBorder = field(
        default_factory=EditableTableBorder
    )

    bottom: EditableTableBorder = field(
        default_factory=EditableTableBorder
    )

    left: EditableTableBorder = field(
        default_factory=EditableTableBorder
    )


@dataclass(slots=True)
class EditableTableCellPadding:
    """
    Word cell margins measured in points.
    """

    top: float = 2.0

    right: float = 3.0

    bottom: float = 2.0

    left: float = 3.0

    def __post_init__(
        self,
    ) -> None:
        self.top = max(
            float(
                self.top
            ),
            0.0,
        )

        self.right = max(
            float(
                self.right
            ),
            0.0,
        )

        self.bottom = max(
            float(
                self.bottom
            ),
            0.0,
        )

        self.left = max(
            float(
                self.left
            ),
            0.0,
        )


@dataclass(slots=True)
class EditableTableColumn:
    """
    One normalized logical table column.
    """

    column_index: int

    left: float

    right: float

    confidence: float = 0.0

    @property
    def width(
        self,
    ) -> float:
        return max(
            float(
                self.right
            )
            - float(
                self.left
            ),
            0.0,
        )

    def __post_init__(
        self,
    ) -> None:
        if self.column_index < 0:
            raise ValueError(
                "column_index must be zero or greater"
            )

        self.left = float(
            self.left
        )

        self.right = float(
            self.right
        )

        if self.right < self.left:
            raise ValueError(
                "column right edge cannot be before left edge"
            )

        self.confidence = clamp_confidence(
            self.confidence
        )


@dataclass(slots=True)
class EditableTableRow:
    """
    One normalized logical table row.
    """

    row_index: int

    top: float

    bottom: float

    is_header: bool = False

    confidence: float = 0.0

    @property
    def height(
        self,
    ) -> float:
        return max(
            float(
                self.bottom
            )
            - float(
                self.top
            ),
            0.0,
        )

    def __post_init__(
        self,
    ) -> None:
        if self.row_index < 0:
            raise ValueError(
                "row_index must be zero or greater"
            )

        self.top = float(
            self.top
        )

        self.bottom = float(
            self.bottom
        )

        if self.bottom < self.top:
            raise ValueError(
                "row bottom edge cannot be before top edge"
            )

        self.confidence = clamp_confidence(
            self.confidence
        )


@dataclass(slots=True)
class EditableTableCell:
    """
    One anchor cell in the normalized editable table grid.

    Cells covered by this cell's row_span or column_span are
    not stored as additional anchor cells.
    """

    row_index: int

    column_index: int

    bbox: Rectangle

    text: str = ""

    row_span: int = 1

    column_span: int = 1

    paragraph_region_numbers: list[int] = field(
        default_factory=list
    )

    paragraphs: list[Any] = field(
        default_factory=list,
        repr=False,
    )

    borders: EditableTableCellBorders = field(
        default_factory=EditableTableCellBorders
    )

    fill_color: str | None = None

    horizontal_alignment: (
        EditableCellHorizontalAlignment
    ) = EditableCellHorizontalAlignment.UNKNOWN

    vertical_alignment: (
        EditableCellVerticalAlignment
    ) = EditableCellVerticalAlignment.TOP

    padding: EditableTableCellPadding = field(
        default_factory=EditableTableCellPadding
    )

    confidence: float = 0.0

    source_cell: Any | None = field(
        default=None,
        repr=False,
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(
        self,
    ) -> None:
        if self.row_index < 0:
            raise ValueError(
                "row_index must be zero or greater"
            )

        if self.column_index < 0:
            raise ValueError(
                "column_index must be zero or greater"
            )

        if self.row_span < 1:
            raise ValueError(
                "row_span must be at least one"
            )

        if self.column_span < 1:
            raise ValueError(
                "column_span must be at least one"
            )

        validate_rectangle(
            self.bbox,
            label="cell bbox",
        )

        self.text = str(
            self.text
            or ""
        )

        self.fill_color = normalize_optional_color(
            self.fill_color
        )

        self.confidence = clamp_confidence(
            self.confidence
        )

        self.paragraph_region_numbers = unique_integers(
            self.paragraph_region_numbers
        )

    @property
    def width(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.right
            )
            - float(
                self.bbox.left
            ),
            0.0,
        )

    @property
    def height(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.bottom
            )
            - float(
                self.bbox.top
            ),
            0.0,
        )

    @property
    def covered_positions(
        self,
    ) -> set[tuple[int, int]]:
        return {
            (
                row_index,
                column_index,
            )

            for row_index in range(
                self.row_index,
                self.row_index
                + self.row_span,
            )

            for column_index in range(
                self.column_index,
                self.column_index
                + self.column_span,
            )
        }

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )


@dataclass(slots=True)
class EditableTable:
    """
    Normalized intermediate representation consumed by the
    native Word-table renderer.
    """

    page_number: int

    table_id: str

    bbox: Rectangle

    row_count: int

    column_count: int

    rows: list[EditableTableRow] = field(
        default_factory=list
    )

    columns: list[EditableTableColumn] = field(
        default_factory=list
    )

    cells: list[EditableTableCell] = field(
        default_factory=list
    )

    disposition: EditableTableDisposition = (
        EditableTableDisposition.EDITABLE
    )

    confidence: float = 0.0

    source_table: Any | None = field(
        default=None,
        repr=False,
    )

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def __post_init__(
        self,
    ) -> None:
        if self.page_number < 1:
            raise ValueError(
                "page_number must be one or greater"
            )

        if self.row_count < 1:
            raise ValueError(
                "row_count must be at least one"
            )

        if self.column_count < 1:
            raise ValueError(
                "column_count must be at least one"
            )

        normalized_id = str(
            self.table_id
        ).strip()

        if not normalized_id:
            raise ValueError(
                "table_id cannot be empty"
            )

        self.table_id = normalized_id

        validate_rectangle(
            self.bbox,
            label="table bbox",
        )

        self.confidence = clamp_confidence(
            self.confidence
        )

    @property
    def width(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.right
            )
            - float(
                self.bbox.left
            ),
            0.0,
        )

    @property
    def height(
        self,
    ) -> float:
        return max(
            float(
                self.bbox.bottom
            )
            - float(
                self.bbox.top
            ),
            0.0,
        )

    @property
    def is_editable(
        self,
    ) -> bool:
        return (
            self.disposition
            == EditableTableDisposition.EDITABLE
        )

    def add_row(
        self,
        row: EditableTableRow,
    ) -> None:
        if row.row_index >= self.row_count:
            raise ValueError(
                "row index is outside the table grid"
            )

        if any(
            existing.row_index
            == row.row_index
            for existing in self.rows
        ):
            raise ValueError(
                (
                    "duplicate editable table row index: "
                    f"{row.row_index}"
                )
            )

        self.rows.append(
            row
        )

        self.rows.sort(
            key=lambda item: item.row_index
        )

    def add_column(
        self,
        column: EditableTableColumn,
    ) -> None:
        if (
            column.column_index
            >= self.column_count
        ):
            raise ValueError(
                "column index is outside the table grid"
            )

        if any(
            existing.column_index
            == column.column_index
            for existing in self.columns
        ):
            raise ValueError(
                (
                    "duplicate editable table column index: "
                    f"{column.column_index}"
                )
            )

        self.columns.append(
            column
        )

        self.columns.sort(
            key=lambda item: item.column_index
        )

    def add_cell(
        self,
        cell: EditableTableCell,
    ) -> None:
        self._validate_cell_bounds(
            cell
        )

        if any(
            existing.row_index
            == cell.row_index
            and existing.column_index
            == cell.column_index
            for existing in self.cells
        ):
            raise ValueError(
                (
                    "duplicate editable table cell anchor: "
                    f"({cell.row_index}, "
                    f"{cell.column_index})"
                )
            )

        occupied_positions = (
            self.occupied_positions
        )

        overlapping = (
            cell.covered_positions
            & occupied_positions
        )

        if overlapping:
            raise ValueError(
                (
                    "editable table cell overlaps an existing "
                    f"cell at {sorted(overlapping)}"
                )
            )

        self.cells.append(
            cell
        )

        self.cells.sort(
            key=lambda item: (
                item.row_index,
                item.column_index,
            )
        )

    @property
    def occupied_positions(
        self,
    ) -> set[tuple[int, int]]:
        occupied: set[
            tuple[int, int]
        ] = set()

        for cell in self.cells:
            occupied.update(
                cell.covered_positions
            )

        return occupied

    def get_cell(
        self,
        row_index: int,
        column_index: int,
    ) -> EditableTableCell | None:
        for cell in self.cells:
            if (
                row_index,
                column_index,
            ) in cell.covered_positions:
                return cell

        return None

    def validate_structure(
        self,
    ) -> list[str]:
        errors: list[str] = []

        if len(
            self.rows
        ) not in {
            0,
            self.row_count,
        }:
            errors.append(
                (
                    "row definition count does not match "
                    "row_count"
                )
            )

        if len(
            self.columns
        ) not in {
            0,
            self.column_count,
        }:
            errors.append(
                (
                    "column definition count does not match "
                    "column_count"
                )
            )

        expected_positions = {
            (
                row_index,
                column_index,
            )

            for row_index in range(
                self.row_count
            )

            for column_index in range(
                self.column_count
            )
        }

        missing_positions = (
            expected_positions
            - self.occupied_positions
        )

        if missing_positions:
            errors.append(
                (
                    "table grid has uncovered positions: "
                    f"{sorted(missing_positions)}"
                )
            )

        return errors

    @property
    def is_structurally_valid(
        self,
    ) -> bool:
        return not self.validate_structure()

    def add_reason(
        self,
        reason: str,
    ) -> None:
        normalized = str(
            reason
        ).strip()

        if (
            normalized
            and normalized
            not in self.reasons
        ):
            self.reasons.append(
                normalized
            )

    def add_warning(
        self,
        warning: str,
    ) -> None:
        normalized = str(
            warning
        ).strip()

        if (
            normalized
            and normalized
            not in self.warnings
        ):
            self.warnings.append(
                normalized
            )

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        self.confidence = clamp_confidence(
            confidence
        )

    def _validate_cell_bounds(
        self,
        cell: EditableTableCell,
    ) -> None:
        if cell.row_index >= self.row_count:
            raise ValueError(
                "cell row index is outside the table grid"
            )

        if (
            cell.column_index
            >= self.column_count
        ):
            raise ValueError(
                "cell column index is outside the table grid"
            )

        if (
            cell.row_index
            + cell.row_span
            > self.row_count
        ):
            raise ValueError(
                "cell row span exceeds the table grid"
            )

        if (
            cell.column_index
            + cell.column_span
            > self.column_count
        ):
            raise ValueError(
                "cell column span exceeds the table grid"
            )



def validate_rectangle(
    rectangle: Rectangle,
    *,
    label: str,
) -> None:
    if (
        float(
            rectangle.right
        )
        < float(
            rectangle.left
        )
    ):
        raise ValueError(
            f"{label} right edge cannot be before left edge"
        )

    if (
        float(
            rectangle.bottom
        )
        < float(
            rectangle.top
        )
    ):
        raise ValueError(
            f"{label} bottom edge cannot be before top edge"
        )


def clamp_confidence(
    confidence: float,
) -> float:
    return max(
        0.0,
        min(
            float(
                confidence
            ),
            1.0,
        ),
    )


def normalize_optional_color(
    color: str | None,
) -> str | None:
    if color is None:
        return None

    normalized = str(
        color
    ).strip().lstrip(
        "#"
    ).upper()

    if re_full_hex(
        normalized
    ):
        return normalized

    return None


def re_full_hex(
    value: str,
) -> bool:
    if len(
        value
    ) != 6:
        return False

    return all(
        character
        in "0123456789ABCDEF"
        for character in value
    )


def unique_integers(
    values: list[int],
) -> list[int]:
    result: list[int] = []

    for value in values:
        try:
            normalized = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if normalized not in result:
            result.append(
                normalized
            )

    return result
