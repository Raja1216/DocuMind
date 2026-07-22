from __future__ import annotations

from statistics import mean
from typing import Any

from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableTable,
    EditableTableCell,
    EditableTableDisposition,
    clamp_confidence,
)
from src.models.geometry.rectangle import (
    Rectangle,
)


class EditableTableMergeDetector:
    """
    Conservatively infer merged table cells.

    A real anchor cell may expand only into repaired synthetic
    blank cells. Another real extracted cell is never consumed.

    Primary evidence:

    1. The original source-cell rectangle crosses reconstructed
       row or column boundaries.
    2. Every newly covered position contains a synthetic blank
       cell.

    Internal border absence is used as supporting evidence.
    """

    SOURCE_GEOMETRY_TOLERANCE = 4.0

    BORDER_WIDTH_ZERO_TOLERANCE = 0.05

    MINIMUM_MERGE_CONFIDENCE = 0.72

    MAXIMUM_CONFLICT_RATIO = 0.25

    @classmethod
    def detect_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.detect_page(
                page
            )

    @classmethod
    def detect_page(
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
            cls.detect_table(
                table
            )

        return tables

    @classmethod
    def detect_table(
        cls,
        table: EditableTable,
    ) -> EditableTable:
        """
        Detect merged cells in one reconstructed editable table.

        Calling this method repeatedly is safe. Previously inferred
        cells are not expanded again.
        """

        if not table.cells:
            return table

        if (
            len(table.rows)
            != table.row_count
            or len(table.columns)
            != table.column_count
        ):
            table.add_warning(
                (
                    "Merged-cell detection was skipped because "
                    "the reconstructed row or column definitions "
                    "are incomplete."
                )
            )

            return table

        if not table.is_structurally_valid:
            table.add_warning(
                (
                    "Merged-cell detection was skipped because "
                    "the reconstructed table grid is invalid."
                )
            )

            return table

        row_boundaries = (
            cls._row_boundaries(
                table
            )
        )

        column_boundaries = (
            cls._column_boundaries(
                table
            )
        )

        # Snapshot the candidates because synthetic cells will be
        # removed while merges are applied.
        candidate_cells = [
            cell

            for cell in table.cells

            if (
                not cell.is_synthetic

                and not cell.merge_inferred

                # Explicit extraction-side merged cells must be
                # preserved without being re-inferred.
                and cell.row_span == 1

                and cell.column_span == 1
            )
        ]

        inferred_confidences: list[
            float
        ] = []

        evaluated_proposal_count = 0

        conflict_count = 0

        for cell in candidate_cells:
            if not cls._cell_has_content(
                cell
            ):
                # Inferring an empty merged cell is risky. Explicit
                # blank merged cells are still preserved because
                # they already have row_span or column_span > 1.
                continue

            source_bbox = cls._extract_bbox(
                cell.source_cell
            )

            if source_bbox is None:
                continue

            (
                proposed_row_span,
                row_geometry_confidence,
            ) = cls._infer_axis_span(
                source_start=float(
                    source_bbox.top
                ),

                source_end=float(
                    source_bbox.bottom
                ),

                start_index=(
                    cell.row_index
                ),

                current_span=(
                    cell.row_span
                ),

                boundaries=(
                    row_boundaries
                ),
            )

            (
                proposed_column_span,
                column_geometry_confidence,
            ) = cls._infer_axis_span(
                source_start=float(
                    source_bbox.left
                ),

                source_end=float(
                    source_bbox.right
                ),

                start_index=(
                    cell.column_index
                ),

                current_span=(
                    cell.column_span
                ),

                boundaries=(
                    column_boundaries
                ),
            )

            if (
                proposed_row_span
                == cell.row_span

                and proposed_column_span
                == cell.column_span
            ):
                continue

            evaluated_proposal_count += 1

            position_map = (
                cls._build_position_map(
                    table
                )
            )

            (
                proposal_is_safe,
                synthetic_cells,
                conflicting_positions,
            ) = cls._validate_proposal(
                table=table,

                cell=cell,

                proposed_row_span=(
                    proposed_row_span
                ),

                proposed_column_span=(
                    proposed_column_span
                ),

                position_map=(
                    position_map
                ),
            )

            if not proposal_is_safe:
                conflict_count += 1

                cell.add_warning(
                    (
                        "Merge proposal conflicts with real "
                        "table content at positions "
                        f"{sorted(conflicting_positions)}."
                    )
                )

                table.add_warning(
                    (
                        "A merged-cell proposal was rejected "
                        "because it would consume another real "
                        "table cell."
                    )
                )

                continue

            geometry_confidences = [
                confidence

                for confidence in {
                    row_geometry_confidence,
                    column_geometry_confidence,
                }

                if confidence > 0.0
            ]

            geometry_confidence = (
                mean(
                    geometry_confidences
                )

                if geometry_confidences

                else 0.0
            )

            border_absence_ratio = (
                cls._internal_border_absence_ratio(
                    cell=cell,

                    proposed_row_span=(
                        proposed_row_span
                    ),

                    proposed_column_span=(
                        proposed_column_span
                    ),

                    position_map=(
                        position_map
                    ),
                )
            )

            newly_covered_position_count = (
                proposed_row_span
                * proposed_column_span

                - cell.row_span
                * cell.column_span
            )

            synthetic_coverage_ratio = (
                len(
                    synthetic_cells
                )
                / max(
                    newly_covered_position_count,
                    1,
                )
            )

            merge_confidence = (
                0.75
                * geometry_confidence

                + 0.15
                * border_absence_ratio

                + 0.10
                * synthetic_coverage_ratio
            )

            merge_confidence = (
                clamp_confidence(
                    merge_confidence
                )
            )

            if (
                merge_confidence
                < cls.MINIMUM_MERGE_CONFIDENCE
            ):
                cell.add_warning(
                    (
                        "Inferred merged-cell confidence "
                        f"{merge_confidence:.3f} is below "
                        f"{cls.MINIMUM_MERGE_CONFIDENCE:.2f}."
                    )
                )

                continue

            cls._apply_merge(
                table=table,

                cell=cell,

                proposed_row_span=(
                    proposed_row_span
                ),

                proposed_column_span=(
                    proposed_column_span
                ),

                synthetic_cells=(
                    synthetic_cells
                ),

                confidence=(
                    merge_confidence
                ),
            )

            inferred_confidences.append(
                merge_confidence
            )

        cls._finalize_table(
            table=table,

            inferred_confidences=(
                inferred_confidences
            ),

            conflict_count=(
                conflict_count
            ),

            evaluated_proposal_count=(
                evaluated_proposal_count
            ),
        )

        return table

    # ---------------------------------------------------------
    # Span inference
    # ---------------------------------------------------------

    @classmethod
    def _infer_axis_span(
        cls,
        *,
        source_start: float,
        source_end: float,
        start_index: int,
        current_span: int,
        boundaries: list[float],
    ) -> tuple[int, float]:
        """
        Infer how many logical rows or columns are covered by one
        source rectangle.
        """

        if (
            start_index < 0

            or start_index
            + current_span
            >= len(boundaries)
        ):
            return (
                current_span,
                0.0,
            )

        expected_start = float(
            boundaries[
                start_index
            ]
        )

        start_distance = abs(
            float(
                source_start
            )
            - expected_start
        )

        if (
            start_distance
            > cls.SOURCE_GEOMETRY_TOLERANCE
        ):
            return (
                current_span,
                0.0,
            )

        minimum_end_index = (
            start_index
            + current_span
        )

        nearest_end_index = None
        nearest_end_distance = None

        for boundary_index in range(
            minimum_end_index,
            len(boundaries),
        ):
            distance = abs(
                float(
                    source_end
                )
                - float(
                    boundaries[
                        boundary_index
                    ]
                )
            )

            if (
                nearest_end_distance is None

                or distance
                < nearest_end_distance
            ):
                nearest_end_index = (
                    boundary_index
                )

                nearest_end_distance = (
                    distance
                )

        if (
            nearest_end_index is None

            or nearest_end_distance is None

            or nearest_end_distance
            > cls.SOURCE_GEOMETRY_TOLERANCE
        ):
            return (
                current_span,
                0.0,
            )

        inferred_span = (
            nearest_end_index
            - start_index
        )

        if inferred_span <= current_span:
            return (
                current_span,
                0.0,
            )

        maximum_distance = max(
            start_distance,
            nearest_end_distance,
        )

        confidence = max(
            0.75,

            1.0
            - (
                maximum_distance
                / cls
                .SOURCE_GEOMETRY_TOLERANCE
            )
            * 0.25,
        )

        return (
            inferred_span,
            clamp_confidence(
                confidence
            ),
        )

    @classmethod
    def _validate_proposal(
        cls,
        *,
        table: EditableTable,
        cell: EditableTableCell,
        proposed_row_span: int,
        proposed_column_span: int,
        position_map: dict[
            tuple[int, int],
            EditableTableCell,
        ],
    ) -> tuple[
        bool,
        list[EditableTableCell],
        set[tuple[int, int]],
    ]:
        if (
            cell.row_index
            + proposed_row_span
            > table.row_count

            or cell.column_index
            + proposed_column_span
            > table.column_count
        ):
            return (
                False,
                [],
                set(),
            )

        proposed_positions = {
            (
                row_index,
                column_index,
            )

            for row_index in range(
                cell.row_index,
                cell.row_index
                + proposed_row_span,
            )

            for column_index in range(
                cell.column_index,
                cell.column_index
                + proposed_column_span,
            )
        }

        newly_covered_positions = (
            proposed_positions
            - cell.covered_positions
        )

        synthetic_cells_by_identity: dict[
            int,
            EditableTableCell,
        ] = {}

        conflicting_positions: set[
            tuple[int, int]
        ] = set()

        for position in (
            newly_covered_positions
        ):
            occupying_cell = (
                position_map.get(
                    position
                )
            )

            if (
                occupying_cell is None

                or not occupying_cell
                .is_synthetic

                or cls._cell_has_content(
                    occupying_cell
                )
            ):
                conflicting_positions.add(
                    position
                )

                continue

            synthetic_cells_by_identity[
                id(
                    occupying_cell
                )
            ] = occupying_cell

        return (
            not conflicting_positions,

            list(
                synthetic_cells_by_identity
                .values()
            ),

            conflicting_positions,
        )

    # ---------------------------------------------------------
    # Border evidence
    # ---------------------------------------------------------

    @classmethod
    def _internal_border_absence_ratio(
        cls,
        *,
        cell: EditableTableCell,
        proposed_row_span: int,
        proposed_column_span: int,
        position_map: dict[
            tuple[int, int],
            EditableTableCell,
        ],
    ) -> float:
        evidence: list[bool] = []

        start_row = cell.row_index

        end_row = (
            cell.row_index
            + proposed_row_span
        )

        start_column = (
            cell.column_index
        )

        end_column = (
            cell.column_index
            + proposed_column_span
        )

        # Check vertical borders between proposed columns.
        for boundary_column in range(
            start_column + 1,
            end_column,
        ):
            for row_index in range(
                start_row,
                end_row,
            ):
                left_cell = (
                    position_map.get(
                        (
                            row_index,
                            boundary_column - 1,
                        )
                    )
                )

                right_cell = (
                    position_map.get(
                        (
                            row_index,
                            boundary_column,
                        )
                    )
                )

                if (
                    left_cell is None
                    or right_cell is None
                ):
                    continue

                if left_cell is right_cell:
                    evidence.append(
                        True
                    )

                else:
                    evidence.append(
                        cls._border_is_absent(
                            left_cell
                            .borders
                            .right
                        )
                        and cls._border_is_absent(
                            right_cell
                            .borders
                            .left
                        )
                    )

        # Check horizontal borders between proposed rows.
        for boundary_row in range(
            start_row + 1,
            end_row,
        ):
            for column_index in range(
                start_column,
                end_column,
            ):
                upper_cell = (
                    position_map.get(
                        (
                            boundary_row - 1,
                            column_index,
                        )
                    )
                )

                lower_cell = (
                    position_map.get(
                        (
                            boundary_row,
                            column_index,
                        )
                    )
                )

                if (
                    upper_cell is None
                    or lower_cell is None
                ):
                    continue

                if upper_cell is lower_cell:
                    evidence.append(
                        True
                    )

                else:
                    evidence.append(
                        cls._border_is_absent(
                            upper_cell
                            .borders
                            .bottom
                        )
                        and cls._border_is_absent(
                            lower_cell
                            .borders
                            .top
                        )
                    )

        if not evidence:
            return 0.0

        return (
            sum(
                1
                for border_is_absent
                in evidence

                if border_is_absent
            )
            / len(
                evidence
            )
        )

    @classmethod
    def _border_is_absent(
        cls,
        border,
    ) -> bool:
        return (
            getattr(
                border,
                "style",
                None,
            )
            == EditableBorderLineStyle.NONE

            or float(
                getattr(
                    border,
                    "width",
                    0.0,
                )
            )
            <= cls.BORDER_WIDTH_ZERO_TOLERANCE
        )

    # ---------------------------------------------------------
    # Apply and validate
    # ---------------------------------------------------------

    @classmethod
    def _apply_merge(
        cls,
        *,
        table: EditableTable,
        cell: EditableTableCell,
        proposed_row_span: int,
        proposed_column_span: int,
        synthetic_cells: list[
            EditableTableCell
        ],
        confidence: float,
    ) -> None:
        synthetic_cell_ids = {
            id(
                synthetic_cell
            )

            for synthetic_cell
            in synthetic_cells
        }

        table.cells = [
            existing_cell

            for existing_cell
            in table.cells

            if id(
                existing_cell
            )
            not in synthetic_cell_ids
        ]

        cell.row_span = int(
            proposed_row_span
        )

        cell.column_span = int(
            proposed_column_span
        )

        final_column = (
            cell.column_index
            + cell.column_span
            - 1
        )

        final_row = (
            cell.row_index
            + cell.row_span
            - 1
        )

        cell.bbox = Rectangle(
            left=float(
                table.columns[
                    cell.column_index
                ].left
            ),

            top=float(
                table.rows[
                    cell.row_index
                ].top
            ),

            right=float(
                table.columns[
                    final_column
                ].right
            ),

            bottom=float(
                table.rows[
                    final_row
                ].bottom
            ),
        )

        cell.merge_inferred = True

        cell.merge_confidence = (
            clamp_confidence(
                confidence
            )
        )

        cell.confidence = (
            clamp_confidence(
                0.75
                * float(
                    cell.confidence
                )

                + 0.25
                * confidence
            )
        )

        cell.add_warning(
            (
                "Merged-cell span was inferred from original "
                "source geometry and synthetic blank-grid "
                "positions."
            )
        )

        table.add_reason(
            (
                "At least one merged-cell span was inferred "
                "from source geometry and reconstructed "
                "synthetic cells."
            )
        )

        table.cells.sort(
            key=lambda current_cell: (
                current_cell.row_index,
                current_cell.column_index,
            )
        )

    @classmethod
    def _finalize_table(
        cls,
        *,
        table: EditableTable,
        inferred_confidences: list[float],
        conflict_count: int,
        evaluated_proposal_count: int,
    ) -> None:
        structure_errors = (
            table.validate_structure()
        )

        for error in structure_errors:
            table.add_warning(
                error
            )

        if structure_errors:
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            table.add_reason(
                (
                    "Merged-cell detection left the table "
                    "grid structurally invalid."
                )
            )

            return

        conflict_ratio = (
            conflict_count
            / evaluated_proposal_count

            if evaluated_proposal_count > 0

            else 0.0
        )

        if (
            conflict_ratio
            > cls.MAXIMUM_CONFLICT_RATIO
        ):
            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            table.add_reason(
                (
                    "Too many merged-cell proposals conflicted "
                    "with real table content."
                )
            )

            return

        if inferred_confidences:
            table.set_confidence(
                0.80
                * float(
                    table.confidence
                )

                + 0.20
                * mean(
                    inferred_confidences
                )
            )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _row_boundaries(
        table: EditableTable,
    ) -> list[float]:
        rows = sorted(
            table.rows,
            key=lambda row: row.row_index,
        )

        return [
            float(
                rows[0].top
            ),

            *[
                float(
                    row.bottom
                )

                for row in rows
            ],
        ]

    @staticmethod
    def _column_boundaries(
        table: EditableTable,
    ) -> list[float]:
        columns = sorted(
            table.columns,
            key=lambda column: (
                column.column_index
            ),
        )

        return [
            float(
                columns[0].left
            ),

            *[
                float(
                    column.right
                )

                for column in columns
            ],
        ]

    @staticmethod
    def _build_position_map(
        table: EditableTable,
    ) -> dict[
        tuple[int, int],
        EditableTableCell,
    ]:
        result: dict[
            tuple[int, int],
            EditableTableCell,
        ] = {}

        for cell in table.cells:
            for position in (
                cell.covered_positions
            ):
                result[
                    position
                ] = cell

        return result

    @staticmethod
    def _cell_has_content(
        cell: EditableTableCell,
    ) -> bool:
        if str(
            cell.text
            or ""
        ).strip():
            return True

        return any(
            str(
                getattr(
                    paragraph,
                    "text",
                    "",
                )
                or ""
            ).strip()

            for paragraph in (
                cell.content_paragraphs
            )
        )

    @staticmethod
    def _extract_bbox(
        source: Any,
    ) -> Rectangle | None:
        if source is None:
            return None

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

        raw_values = [
            getattr(
                geometry_source,
                attribute_name,
                None,
            )

            for attribute_name in {
                "left",
                "top",
                "right",
                "bottom",
            }
        ]

        if any(
            value is None
            for value in raw_values
        ):
            return None

        try:
            left = float(
                getattr(
                    geometry_source,
                    "left"
                )
            )

            top = float(
                getattr(
                    geometry_source,
                    "top"
                )
            )

            right = float(
                getattr(
                    geometry_source,
                    "right"
                )
            )

            bottom = float(
                getattr(
                    geometry_source,
                    "bottom"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if right < left:
            left, right = (
                right,
                left,
            )

        if bottom < top:
            top, bottom = (
                bottom,
                top,
            )

        return Rectangle(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )