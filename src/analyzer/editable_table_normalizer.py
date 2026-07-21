from __future__ import annotations

from statistics import median
from typing import Any

from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableCellHorizontalAlignment,
    EditableCellVerticalAlignment,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableColumn,
    EditableTableDisposition,
    EditableTableRow,
)
from src.models.geometry.rectangle import Rectangle


class EditableTableNormalizer:
    """
    Convert extraction-side Table/TableCell objects into the
    normalized editable-table intermediate representation.

    This step intentionally performs only direct normalization.
    It does not infer missing rows, columns, merged cells, or
    paragraph-to-cell relationships. Unresolved structures are
    preserved as visual-fallback tables for later reconstruction.
    """

    MINIMUM_EDITABLE_CONFIDENCE = 0.55

    DEFAULT_TABLE_CONFIDENCE = 0.85
    DEFAULT_CELL_CONFIDENCE = 0.90
    DEFAULT_GRID_CONFIDENCE = 0.85
    DEFAULT_BORDER_CONFIDENCE = 0.75

    @classmethod
    def normalize_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.normalize_page(page)

    @classmethod
    def normalize_page(
        cls,
        page,
    ) -> list[EditableTable]:
        """
        Rebuild editable tables for one page.

        Reanalysis replaces stale normalized tables rather than
        appending duplicates.
        """

        normalized_tables: list[EditableTable] = []

        for table_index, source_table in enumerate(
            getattr(
                page,
                "tables",
                [],
            )
            or []
        ):
            normalized_tables.append(
                cls.normalize_table(
                    source_table=source_table,
                    table_index=table_index,
                )
            )

        page.editable_tables = normalized_tables

        return normalized_tables

    @classmethod
    def normalize_table(
        cls,
        source_table,
        table_index: int = 0,
    ) -> EditableTable:
        page_number = cls._positive_integer(
            getattr(
                source_table,
                "page_number",
                1,
            ),
            fallback=1,
        )

        row_count = cls._positive_integer(
            getattr(
                source_table,
                "row_count",
                0,
            ),
            fallback=1,
        )

        column_count = cls._positive_integer(
            getattr(
                source_table,
                "column_count",
                0,
            ),
            fallback=1,
        )

        table = EditableTable(
            page_number=page_number,
            table_id=cls._build_table_id(
                source_table=source_table,
                table_index=table_index,
                page_number=page_number,
            ),
            bbox=cls._rectangle_from_source(
                source_table
            ),
            row_count=row_count,
            column_count=column_count,
            confidence=0.0,
            source_table=source_table,
        )

        source_row_count = cls._safe_integer(
            getattr(
                source_table,
                "row_count",
                None,
            )
        )

        source_column_count = cls._safe_integer(
            getattr(
                source_table,
                "column_count",
                None,
            )
        )

        if source_row_count is None or source_row_count < 1:
            table.add_warning(
                "Source table has no valid row count."
            )

        if (
            source_column_count is None
            or source_column_count < 1
        ):
            table.add_warning(
                "Source table has no valid column count."
            )

        source_cells = list(
            getattr(
                source_table,
                "cells",
                [],
            )
            or []
        )

        mapped_cell_count = cls._add_cells(
            table=table,
            source_table=source_table,
            source_cells=source_cells,
        )

        cls._add_direct_rows(
            table=table
        )

        cls._add_direct_columns(
            table=table
        )

        cls._finalize_table(
            table=table,
            source_cell_count=len(source_cells),
            mapped_cell_count=mapped_cell_count,
        )

        return table

    # ---------------------------------------------------------
    # Cells
    # ---------------------------------------------------------

    @classmethod
    def _add_cells(
        cls,
        table: EditableTable,
        source_table,
        source_cells: list[Any],
    ) -> int:
        mapped_cell_count = 0

        for source_cell in source_cells:
            row_index = cls._safe_integer(
                getattr(
                    source_cell,
                    "row_index",
                    None,
                )
            )

            column_index = cls._safe_integer(
                getattr(
                    source_cell,
                    "column_index",
                    None,
                )
            )

            if row_index is None or column_index is None:
                table.add_warning(
                    "Skipped a source cell without valid row and column indexes."
                )
                continue

            row_span = cls._positive_integer(
                getattr(
                    source_cell,
                    "row_span",
                    1,
                ),
                fallback=1,
            )

            column_span = cls._positive_integer(
                getattr(
                    source_cell,
                    "column_span",
                    1,
                ),
                fallback=1,
            )

            border = cls._build_border(
                source_table
            )

            editable_cell = EditableTableCell(
                row_index=row_index,
                column_index=column_index,
                bbox=cls._rectangle_from_source(
                    source_cell
                ),
                text=str(
                    getattr(
                        source_cell,
                        "text",
                        "",
                    )
                    or ""
                ),
                row_span=row_span,
                column_span=column_span,
                borders=EditableTableCellBorders(
                    top=cls._copy_border(border),
                    right=cls._copy_border(border),
                    bottom=cls._copy_border(border),
                    left=cls._copy_border(border),
                ),
                fill_color=getattr(
                    source_cell,
                    "fill_color",
                    None,
                ),
                horizontal_alignment=(
                    EditableCellHorizontalAlignment.UNKNOWN
                ),
                vertical_alignment=(
                    EditableCellVerticalAlignment.TOP
                ),
                confidence=cls.DEFAULT_CELL_CONFIDENCE,
                source_cell=source_cell,
            )

            try:
                table.add_cell(
                    editable_cell
                )

            except ValueError as error:
                table.add_warning(
                    (
                        "Skipped invalid source cell "
                        f"({row_index}, {column_index}): "
                        f"{error}"
                    )
                )
                continue

            mapped_cell_count += 1

        return mapped_cell_count

    # ---------------------------------------------------------
    # Direct row and column geometry
    # ---------------------------------------------------------

    @classmethod
    def _add_direct_rows(
        cls,
        table: EditableTable,
    ) -> None:
        for row_index in range(
            table.row_count
        ):
            # Prefer cells that belong only to this row. A cell
            # spanning several rows does not reveal the internal
            # row boundary.
            direct_cells = [
                cell
                for cell in table.cells
                if (
                    cell.row_index == row_index
                    and cell.row_span == 1
                )
            ]

            if not direct_cells:
                table.add_warning(
                    (
                        "Direct row geometry is unavailable for "
                        f"row {row_index}; grid reconstruction is required."
                    )
                )
                continue

            top_values = [
                float(
                    cell.bbox.top
                )
                for cell in direct_cells
            ]

            bottom_values = [
                float(
                    cell.bbox.bottom
                )
                for cell in direct_cells
            ]

            table.add_row(
                EditableTableRow(
                    row_index=row_index,
                    top=float(
                        median(top_values)
                    ),
                    bottom=float(
                        median(bottom_values)
                    ),
                    is_header=cls._resolve_header_row(
                        table=table,
                        row_index=row_index,
                    ),
                    confidence=(
                        cls.DEFAULT_GRID_CONFIDENCE
                    ),
                )
            )

    @classmethod
    def _add_direct_columns(
        cls,
        table: EditableTable,
    ) -> None:
        for column_index in range(
            table.column_count
        ):
            # Prefer cells that belong only to this column. A
            # horizontally merged cell cannot define the internal
            # column boundary.
            direct_cells = [
                cell
                for cell in table.cells
                if (
                    cell.column_index == column_index
                    and cell.column_span == 1
                )
            ]

            if not direct_cells:
                table.add_warning(
                    (
                        "Direct column geometry is unavailable for "
                        f"column {column_index}; grid reconstruction is required."
                    )
                )
                continue

            left_values = [
                float(
                    cell.bbox.left
                )
                for cell in direct_cells
            ]

            right_values = [
                float(
                    cell.bbox.right
                )
                for cell in direct_cells
            ]

            table.add_column(
                EditableTableColumn(
                    column_index=column_index,
                    left=float(
                        median(left_values)
                    ),
                    right=float(
                        median(right_values)
                    ),
                    confidence=(
                        cls.DEFAULT_GRID_CONFIDENCE
                    ),
                )
            )

    # ---------------------------------------------------------
    # Final strategy and confidence
    # ---------------------------------------------------------

    @classmethod
    def _finalize_table(
        cls,
        table: EditableTable,
        source_cell_count: int,
        mapped_cell_count: int,
    ) -> None:
        total_positions = max(
            table.row_count
            * table.column_count,
            1,
        )

        coverage_ratio = min(
            len(
                table.occupied_positions
            )
            / total_positions,
            1.0,
        )

        mapped_ratio = (
            mapped_cell_count
            / source_cell_count
            if source_cell_count > 0
            else 0.0
        )

        row_ratio = min(
            len(
                table.rows
            )
            / table.row_count,
            1.0,
        )

        column_ratio = min(
            len(
                table.columns
            )
            / table.column_count,
            1.0,
        )

        confidence = (
            0.10
            + 0.40 * coverage_ratio
            + 0.20 * mapped_ratio
            + 0.15 * row_ratio
            + 0.15 * column_ratio
        )

        table.set_confidence(
            confidence
        )

        structure_errors = (
            table.validate_structure()
        )

        for error in structure_errors:
            table.add_warning(
                error
            )

        if source_cell_count == 0:
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            table.add_reason(
                "Source table contains no mapped cells."
            )

            return

        if structure_errors:
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            table.add_reason(
                (
                    "The directly normalized table grid is "
                    "incomplete and requires reconstruction."
                )
            )

            return

        if (
            table.confidence
            < cls.MINIMUM_EDITABLE_CONFIDENCE
        ):
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            table.add_reason(
                (
                    "Normalized table confidence is below the "
                    "editable-table threshold."
                )
            )

            return

        table.disposition = (
            EditableTableDisposition.EDITABLE
        )

        table.add_reason(
            (
                "Extraction-side cells form a complete, direct "
                "editable table grid."
            )
        )

    # ---------------------------------------------------------
    # Source normalization
    # ---------------------------------------------------------

    @classmethod
    def _build_border(
        cls,
        source_table,
    ) -> EditableTableBorder:
        border_style = getattr(
            source_table,
            "border_style",
            None,
        )

        width = cls._safe_float(
            getattr(
                border_style,
                "thickness",
                0.5,
            ),
            fallback=0.5,
        )

        line_style = (
            EditableBorderLineStyle.SINGLE
            if width > 0.0
            else EditableBorderLineStyle.NONE
        )

        return EditableTableBorder(
            style=line_style,
            color=getattr(
                border_style,
                "color",
                "B7B7B7",
            ),
            width=width,
            confidence=cls.DEFAULT_BORDER_CONFIDENCE,
        )

    @staticmethod
    def _copy_border(
        border: EditableTableBorder,
    ) -> EditableTableBorder:
        return EditableTableBorder(
            style=border.style,
            color=border.color,
            width=border.width,
            confidence=border.confidence,
        )

    @staticmethod
    def _resolve_header_row(
        table: EditableTable,
        row_index: int,
    ) -> bool:
        source_table = table.source_table

        explicit_header_rows = getattr(
            source_table,
            "header_row_indexes",
            None,
        )

        if explicit_header_rows is not None:
            try:
                return row_index in {
                    int(value)
                    for value in explicit_header_rows
                }
            except TypeError:
                pass

        header_row_count = getattr(
            source_table,
            "header_row_count",
            None,
        )

        try:
            if header_row_count is not None:
                return row_index < max(
                    int(
                        header_row_count
                    ),
                    0,
                )
        except (
            TypeError,
            ValueError,
        ):
            pass

        return False

    @classmethod
    def _build_table_id(
        cls,
        source_table,
        table_index: int,
        page_number: int,
    ) -> str:
        for attribute_name in (
            "table_id",
            "table_number",
            "id",
        ):
            value = getattr(
                source_table,
                attribute_name,
                None,
            )

            if value is None:
                continue

            normalized = str(
                value
            ).strip()

            if normalized:
                return (
                    f"table:{page_number}:{normalized}"
                )

        return (
            f"table:{page_number}:{table_index + 1}"
        )

    @staticmethod
    def _rectangle_from_source(
        source,
    ) -> Rectangle:
        bbox = getattr(
            source,
            "bbox",
            None,
        )

        geometry_source = (
            bbox
            if bbox is not None
            else source
        )

        left = EditableTableNormalizer._safe_float(
            getattr(
                geometry_source,
                "left",
                0.0,
            ),
            fallback=0.0,
        )

        top = EditableTableNormalizer._safe_float(
            getattr(
                geometry_source,
                "top",
                0.0,
            ),
            fallback=0.0,
        )

        right = EditableTableNormalizer._safe_float(
            getattr(
                geometry_source,
                "right",
                left,
            ),
            fallback=left,
        )

        bottom = EditableTableNormalizer._safe_float(
            getattr(
                geometry_source,
                "bottom",
                top,
            ),
            fallback=top,
        )

        # Keep normalization non-fatal for malformed extraction
        # geometry. The warning/fallback decision is made later.
        if right < left:
            left, right = right, left

        if bottom < top:
            top, bottom = bottom, top

        return Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )

    @staticmethod
    def _positive_integer(
        value,
        *,
        fallback: int,
    ) -> int:
        try:
            normalized = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return fallback

        return (
            normalized
            if normalized > 0
            else fallback
        )

    @staticmethod
    def _safe_integer(
        value,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _safe_float(
        value,
        *,
        fallback: float,
    ) -> float:
        try:
            return float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(
                fallback
            )
