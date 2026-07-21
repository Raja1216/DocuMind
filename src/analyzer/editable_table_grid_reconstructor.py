from __future__ import annotations

from statistics import mean, median
from typing import Any, Callable

from src.models.editable_table import (
    EditableCellHorizontalAlignment,
    EditableCellVerticalAlignment,
    EditableTable,
    EditableTableBorder,
    EditableTableCell,
    EditableTableCellBorders,
    EditableTableCellPadding,
    EditableTableColumn,
    EditableTableDisposition,
    EditableTableRow,
    clamp_confidence,
)
from src.models.geometry.rectangle import Rectangle


class EditableTableGridReconstructor:
    """
    Reconstruct complete row and column geometry for normalized
    editable tables.

    The normalizer preserves direct extraction geometry. This
    analyzer resolves missing internal grid boundaries from cell
    indexes and spans, snaps cells to that grid, and creates
    low-confidence synthetic blank cells for uncovered positions.

    It does not infer new merged-cell spans. Synthetic cells remain
    identifiable so the later merged-cell analyzer can combine them
    when border evidence supports a merge.
    """

    BOUNDARY_CONFLICT_TOLERANCE = 3.0
    MAXIMUM_SNAP_DISTANCE = 4.0
    MINIMUM_SEGMENT_SIZE = 0.5

    DIRECT_BOUNDARY_CONFIDENCE = 0.95
    CONFLICTED_BOUNDARY_CONFIDENCE = 0.70
    INTERPOLATED_BOUNDARY_CONFIDENCE = 0.60
    UNIFORM_FALLBACK_CONFIDENCE = 0.40
    SYNTHETIC_CELL_CONFIDENCE = 0.45

    MINIMUM_EDITABLE_CONFIDENCE = 0.55
    MAXIMUM_EDITABLE_SYNTHETIC_RATIO = 0.35

    _STALE_WARNING_FRAGMENTS = (
        "direct row geometry is unavailable",
        "direct column geometry is unavailable",
        "row definition count does not match",
        "column definition count does not match",
        "table grid has uncovered positions",
    )

    _STALE_REASON_FRAGMENTS = (
        "directly normalized table grid is incomplete",
        "requires reconstruction",
    )

    @classmethod
    def reconstruct_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.reconstruct_page(page)

    @classmethod
    def reconstruct_page(
        cls,
        page,
    ) -> list[EditableTable]:
        tables = list(
            getattr(
                page,
                "editable_tables",
                [],
            )
            or []
        )

        for table in tables:
            cls.reconstruct_table(table)

        return tables

    @classmethod
    def reconstruct_table(
        cls,
        table: EditableTable,
    ) -> EditableTable:
        cls._remove_stale_messages(table)

        if not table.cells:
            table.rows.clear()
            table.columns.clear()
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )
            table.set_confidence(
                min(
                    table.confidence,
                    cls.UNIFORM_FALLBACK_CONFIDENCE,
                )
            )
            table.add_reason(
                "Table grid cannot be reconstructed without cell geometry."
            )
            return table

        existing_header_rows = {
            row.row_index: row.is_header
            for row in table.rows
        }

        row_boundaries, row_boundary_confidence = (
            cls._resolve_axis_boundaries(
                table=table,
                count=table.row_count,
                outer_start=float(table.bbox.top),
                outer_end=float(table.bbox.bottom),
                existing_segments=table.rows,
                cells=table.cells,
                segment_index=lambda cell: cell.row_index,
                segment_span=lambda cell: cell.row_span,
                cell_start=lambda cell: float(cell.bbox.top),
                cell_end=lambda cell: float(cell.bbox.bottom),
                existing_index=lambda row: row.row_index,
                existing_start=lambda row: float(row.top),
                existing_end=lambda row: float(row.bottom),
                axis_name="row",
            )
        )

        column_boundaries, column_boundary_confidence = (
            cls._resolve_axis_boundaries(
                table=table,
                count=table.column_count,
                outer_start=float(table.bbox.left),
                outer_end=float(table.bbox.right),
                existing_segments=table.columns,
                cells=table.cells,
                segment_index=lambda cell: cell.column_index,
                segment_span=lambda cell: cell.column_span,
                cell_start=lambda cell: float(cell.bbox.left),
                cell_end=lambda cell: float(cell.bbox.right),
                existing_index=lambda column: column.column_index,
                existing_start=lambda column: float(column.left),
                existing_end=lambda column: float(column.right),
                axis_name="column",
            )
        )

        cls._replace_rows(
            table=table,
            boundaries=row_boundaries,
            boundary_confidence=(
                row_boundary_confidence
            ),
            existing_header_rows=(
                existing_header_rows
            ),
        )

        cls._replace_columns(
            table=table,
            boundaries=column_boundaries,
            boundary_confidence=(
                column_boundary_confidence
            ),
        )

        grid_confidence = mean(
            row_boundary_confidence
            + column_boundary_confidence
        )

        cls._snap_existing_cells(
            table=table,
            row_boundaries=row_boundaries,
            column_boundaries=(
                column_boundaries
            ),
            grid_confidence=grid_confidence,
        )

        synthetic_cell_count = (
            cls._fill_missing_positions(
                table=table,
                row_boundaries=row_boundaries,
                column_boundaries=(
                    column_boundaries
                ),
            )
        )

        cls._finalize_reconstructed_table(
            table=table,
            grid_confidence=grid_confidence,
            synthetic_cell_count=(
                synthetic_cell_count
            ),
        )

        return table

    # ---------------------------------------------------------
    # Axis reconstruction
    # ---------------------------------------------------------

    @classmethod
    def _resolve_axis_boundaries(
        cls,
        *,
        table: EditableTable,
        count: int,
        outer_start: float,
        outer_end: float,
        existing_segments: list[Any],
        cells: list[EditableTableCell],
        segment_index: Callable[[EditableTableCell], int],
        segment_span: Callable[[EditableTableCell], int],
        cell_start: Callable[[EditableTableCell], float],
        cell_end: Callable[[EditableTableCell], float],
        existing_index: Callable[[Any], int],
        existing_start: Callable[[Any], float],
        existing_end: Callable[[Any], float],
        axis_name: str,
    ) -> tuple[list[float], list[float]]:
        candidates: list[list[float]] = [
            []
            for _ in range(count + 1)
        ]

        candidates[0].append(
            float(outer_start)
        )
        candidates[count].append(
            float(outer_end)
        )

        for segment in existing_segments:
            index = existing_index(segment)

            if not 0 <= index < count:
                continue

            candidates[index].append(
                existing_start(segment)
            )
            candidates[index + 1].append(
                existing_end(segment)
            )

        for cell in cells:
            index = int(
                segment_index(cell)
            )
            span = int(
                segment_span(cell)
            )

            if (
                index < 0
                or span < 1
                or index + span > count
            ):
                continue

            candidates[index].append(
                cell_start(cell)
            )
            candidates[index + span].append(
                cell_end(cell)
            )

        boundaries: list[float | None] = [
            None
            for _ in range(count + 1)
        ]
        confidence: list[float] = [
            0.0
            for _ in range(count + 1)
        ]

        for boundary_index, values in enumerate(
            candidates
        ):
            if not values:
                continue

            boundary_value = float(
                median(values)
            )
            spread = max(values) - min(values)

            boundaries[boundary_index] = (
                boundary_value
            )
            confidence[boundary_index] = (
                cls.DIRECT_BOUNDARY_CONFIDENCE
                if spread
                <= cls.BOUNDARY_CONFLICT_TOLERANCE
                else cls.CONFLICTED_BOUNDARY_CONFIDENCE
            )

            if (
                spread
                > cls.BOUNDARY_CONFLICT_TOLERANCE
            ):
                table.add_warning(
                    (
                        f"Conflicting {axis_name} boundary "
                        f"geometry at index {boundary_index}; "
                        "the median coordinate was used."
                    )
                )

        # The normalized table rectangle owns the outside edges.
        boundaries[0] = float(outer_start)
        boundaries[count] = float(outer_end)
        confidence[0] = (
            cls.DIRECT_BOUNDARY_CONFIDENCE
        )
        confidence[count] = (
            cls.DIRECT_BOUNDARY_CONFIDENCE
        )

        cls._interpolate_missing_boundaries(
            boundaries=boundaries,
            confidence=confidence,
        )

        resolved = [
            float(value)
            for value in boundaries
            if value is not None
        ]

        if (
            len(resolved) != count + 1
            or not cls._boundaries_are_monotonic(
                resolved
            )
        ):
            table.add_warning(
                (
                    f"{axis_name.capitalize()} boundaries "
                    "were non-monotonic; uniform fallback "
                    "geometry was used."
                )
            )

            resolved = cls._uniform_boundaries(
                start=outer_start,
                end=outer_end,
                count=count,
            )
            confidence = [
                cls.UNIFORM_FALLBACK_CONFIDENCE
                for _ in range(count + 1)
            ]

        return (
            resolved,
            confidence,
        )

    @classmethod
    def _interpolate_missing_boundaries(
        cls,
        *,
        boundaries: list[float | None],
        confidence: list[float],
    ) -> None:
        known_indexes = [
            index
            for index, value in enumerate(
                boundaries
            )
            if value is not None
        ]

        for left_index, right_index in zip(
            known_indexes,
            known_indexes[1:],
        ):
            gap = right_index - left_index

            if gap <= 1:
                continue

            left_value = float(
                boundaries[left_index]
            )
            right_value = float(
                boundaries[right_index]
            )
            step = (
                right_value - left_value
            ) / gap

            for offset in range(1, gap):
                index = left_index + offset
                boundaries[index] = (
                    left_value
                    + step * offset
                )
                confidence[index] = (
                    cls.INTERPOLATED_BOUNDARY_CONFIDENCE
                )

    @classmethod
    def _boundaries_are_monotonic(
        cls,
        boundaries: list[float],
    ) -> bool:
        return all(
            current - previous
            >= cls.MINIMUM_SEGMENT_SIZE
            for previous, current in zip(
                boundaries,
                boundaries[1:],
            )
        )

    @staticmethod
    def _uniform_boundaries(
        *,
        start: float,
        end: float,
        count: int,
    ) -> list[float]:
        step = (
            float(end) - float(start)
        ) / max(count, 1)

        return [
            float(start) + step * index
            for index in range(count + 1)
        ]

    # ---------------------------------------------------------
    # Row and column replacement
    # ---------------------------------------------------------

    @classmethod
    def _replace_rows(
        cls,
        *,
        table: EditableTable,
        boundaries: list[float],
        boundary_confidence: list[float],
        existing_header_rows: dict[int, bool],
    ) -> None:
        table.rows.clear()

        for row_index in range(
            table.row_count
        ):
            table.add_row(
                EditableTableRow(
                    row_index=row_index,
                    top=boundaries[row_index],
                    bottom=boundaries[
                        row_index + 1
                    ],
                    is_header=existing_header_rows.get(
                        row_index,
                        False,
                    ),
                    confidence=min(
                        boundary_confidence[
                            row_index
                        ],
                        boundary_confidence[
                            row_index + 1
                        ],
                    ),
                )
            )

    @classmethod
    def _replace_columns(
        cls,
        *,
        table: EditableTable,
        boundaries: list[float],
        boundary_confidence: list[float],
    ) -> None:
        table.columns.clear()

        for column_index in range(
            table.column_count
        ):
            table.add_column(
                EditableTableColumn(
                    column_index=column_index,
                    left=boundaries[
                        column_index
                    ],
                    right=boundaries[
                        column_index + 1
                    ],
                    confidence=min(
                        boundary_confidence[
                            column_index
                        ],
                        boundary_confidence[
                            column_index + 1
                        ],
                    ),
                )
            )

    # ---------------------------------------------------------
    # Cell repair
    # ---------------------------------------------------------

    @classmethod
    def _snap_existing_cells(
        cls,
        *,
        table: EditableTable,
        row_boundaries: list[float],
        column_boundaries: list[float],
        grid_confidence: float,
    ) -> None:
        for cell in table.cells:
            expected = Rectangle(
                left=column_boundaries[
                    cell.column_index
                ],
                top=row_boundaries[
                    cell.row_index
                ],
                right=column_boundaries[
                    cell.column_index
                    + cell.column_span
                ],
                bottom=row_boundaries[
                    cell.row_index
                    + cell.row_span
                ],
            )

            maximum_delta = max(
                abs(
                    float(cell.bbox.left)
                    - float(expected.left)
                ),
                abs(
                    float(cell.bbox.top)
                    - float(expected.top)
                ),
                abs(
                    float(cell.bbox.right)
                    - float(expected.right)
                ),
                abs(
                    float(cell.bbox.bottom)
                    - float(expected.bottom)
                ),
            )

            cell.bbox = expected
            cell.confidence = clamp_confidence(
                0.70 * float(cell.confidence)
                + 0.30 * float(grid_confidence)
            )

            if (
                maximum_delta
                > cls.MAXIMUM_SNAP_DISTANCE
            ):
                cell.add_warning(
                    (
                        "Cell geometry was snapped to the "
                        "reconstructed grid by more than "
                        f"{cls.MAXIMUM_SNAP_DISTANCE:.1f} points."
                    )
                )

    @classmethod
    def _fill_missing_positions(
        cls,
        *,
        table: EditableTable,
        row_boundaries: list[float],
        column_boundaries: list[float],
    ) -> int:
        expected_positions = {
            (row_index, column_index)
            for row_index in range(
                table.row_count
            )
            for column_index in range(
                table.column_count
            )
        }

        missing_positions = sorted(
            expected_positions
            - table.occupied_positions
        )

        if not missing_positions:
            return len(
                [
                    cell
                    for cell in table.cells
                    if cell.is_synthetic
                ]
            )

        border_template = (
            cls._resolve_border_template(
                table
            )
        )
        padding_template = (
            cls._resolve_padding_template(
                table
            )
        )

        for row_index, column_index in (
            missing_positions
        ):
            synthetic_cell = EditableTableCell(
                row_index=row_index,
                column_index=column_index,
                bbox=Rectangle(
                    left=column_boundaries[
                        column_index
                    ],
                    top=row_boundaries[
                        row_index
                    ],
                    right=column_boundaries[
                        column_index + 1
                    ],
                    bottom=row_boundaries[
                        row_index + 1
                    ],
                ),
                text="",
                borders=cls._copy_borders(
                    border_template
                ),
                horizontal_alignment=(
                    EditableCellHorizontalAlignment
                    .UNKNOWN
                ),
                vertical_alignment=(
                    EditableCellVerticalAlignment.TOP
                ),
                padding=cls._copy_padding(
                    padding_template
                ),
                confidence=(
                    cls.SYNTHETIC_CELL_CONFIDENCE
                ),
                source_cell=None,
                is_synthetic=True,
            )

            synthetic_cell.add_warning(
                (
                    "Synthetic blank cell created to repair "
                    "an uncovered table-grid position."
                )
            )

            table.add_cell(
                synthetic_cell
            )

        return len(
            [
                cell
                for cell in table.cells
                if cell.is_synthetic
            ]
        )

    @classmethod
    def _resolve_border_template(
        cls,
        table: EditableTable,
    ) -> EditableTableCellBorders:
        for cell in table.cells:
            return cell.borders

        return EditableTableCellBorders()

    @classmethod
    def _resolve_padding_template(
        cls,
        table: EditableTable,
    ) -> EditableTableCellPadding:
        for cell in table.cells:
            return cell.padding

        return EditableTableCellPadding()

    @classmethod
    def _copy_borders(
        cls,
        borders: EditableTableCellBorders,
    ) -> EditableTableCellBorders:
        return EditableTableCellBorders(
            top=cls._copy_border(
                borders.top
            ),
            right=cls._copy_border(
                borders.right
            ),
            bottom=cls._copy_border(
                borders.bottom
            ),
            left=cls._copy_border(
                borders.left
            ),
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
    def _copy_padding(
        padding: EditableTableCellPadding,
    ) -> EditableTableCellPadding:
        return EditableTableCellPadding(
            top=padding.top,
            right=padding.right,
            bottom=padding.bottom,
            left=padding.left,
        )

    # ---------------------------------------------------------
    # Finalization
    # ---------------------------------------------------------

    @classmethod
    def _finalize_reconstructed_table(
        cls,
        *,
        table: EditableTable,
        grid_confidence: float,
        synthetic_cell_count: int,
    ) -> None:
        total_positions = max(
            table.row_count
            * table.column_count,
            1,
        )
        synthetic_ratio = min(
            synthetic_cell_count
            / total_positions,
            1.0,
        )
        original_coverage = (
            1.0 - synthetic_ratio
        )

        table.set_confidence(
            0.45 * float(table.confidence)
            + 0.35 * float(grid_confidence)
            + 0.20 * original_coverage
        )

        structure_errors = (
            table.validate_structure()
        )

        for error in structure_errors:
            table.add_warning(error)

        if synthetic_cell_count > 0:
            table.add_warning(
                (
                    f"Created {synthetic_cell_count} "
                    "synthetic blank table cell(s) during "
                    "grid repair."
                )
            )

        if structure_errors:
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )
            table.add_reason(
                "The reconstructed table grid remains structurally invalid."
            )
            return

        if (
            synthetic_ratio
            > cls.MAXIMUM_EDITABLE_SYNTHETIC_RATIO
        ):
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )
            table.add_reason(
                (
                    "Too much of the table grid was synthesized "
                    "for reliable native Word-table export."
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
                "Reconstructed table confidence is below the editable threshold."
            )
            return

        table.disposition = (
            EditableTableDisposition.EDITABLE
        )

        if synthetic_cell_count > 0:
            table.add_reason(
                (
                    "Missing blank grid positions were repaired "
                    "using reconstructed row and column boundaries."
                )
            )
        else:
            table.add_reason(
                (
                    "Row and column boundaries form a complete "
                    "editable table grid."
                )
            )

    @classmethod
    def _remove_stale_messages(
        cls,
        table: EditableTable,
    ) -> None:
        table.warnings = [
            warning
            for warning in table.warnings
            if not any(
                fragment
                in warning.casefold()
                for fragment in (
                    cls._STALE_WARNING_FRAGMENTS
                )
            )
        ]

        table.reasons = [
            reason
            for reason in table.reasons
            if not any(
                fragment
                in reason.casefold()
                for fragment in (
                    cls._STALE_REASON_FRAGMENTS
                )
            )
        ]
