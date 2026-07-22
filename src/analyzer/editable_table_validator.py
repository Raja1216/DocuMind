from __future__ import annotations

import math
from statistics import mean
from typing import Any

from src.models.editable_table import (
    EditableBorderLineStyle,
    EditableTable,
    EditableTableDisposition,
)
from src.models.editable_table_validation import (
    EditableTableRenderDecision,
    EditableTableValidationReport,
    EditableTableValidationSeverity,
    clamp_confidence,
)


class EditableTableValidator:
    """
    Generalized safety validator for native Word-table rendering.

    The validator relies only on structural, geometric, content,
    merge, style and reconstruction evidence. It contains no
    filename-, page-, sample-, text- or fixed-grid-specific rules.
    """

    GEOMETRY_TOLERANCE = 1.5

    WARNING_SYNTHETIC_RATIO = 0.20

    MAXIMUM_NATIVE_SYNTHETIC_RATIO = 0.35

    MINIMUM_NATIVE_INFERRED_MERGE_CONFIDENCE = 0.72

    NATIVE_SAFE_CONFIDENCE = 0.80

    MINIMUM_NATIVE_CONFIDENCE = 0.65

    MINIMUM_RENDERED_COLUMN_WIDTH = 6.0

    DEFAULT_WORD_AVAILABLE_WIDTH = 468.0

    DEFAULT_PAGE_MARGIN = 36.0

    MAXIMUM_NATIVE_COLUMNS = 63

    MAXIMUM_NATIVE_ROWS = 5000

    SUPPORTED_BORDER_STYLES = {
        EditableBorderLineStyle.NONE,
        EditableBorderLineStyle.SINGLE,
        EditableBorderLineStyle.DOUBLE,
        EditableBorderLineStyle.DASHED,
        EditableBorderLineStyle.DOTTED,
    }

    @classmethod
    def validate_document(
        cls,
        document,
    ) -> None:
        for page in getattr(
            document,
            "pages",
            [],
        ) or []:
            cls.validate_page(
                page
            )

    @classmethod
    def validate_page(
        cls,
        page,
    ) -> dict[
        str,
        EditableTableValidationReport,
    ]:
        reports: dict[
            str,
            EditableTableValidationReport,
        ] = {}

        available_width = (
            cls._resolve_available_width(
                page
            )
        )

        for table in getattr(
            page,
            "editable_tables",
            [],
        ) or []:
            report = cls.validate_table(
                table=table,
                available_width=available_width,
            )

            reports[
                table.table_id
            ] = report

        # Reanalysis replaces stale reports.
        page.editable_table_validation_reports = (
            reports
        )

        return reports

    @classmethod
    def validate_table(
        cls,
        *,
        table: EditableTable,
        available_width: float | None = None,
    ) -> EditableTableValidationReport:
        report = EditableTableValidationReport(
            table_id=table.table_id,
            page_number=table.page_number,
        )

        resolved_available_width = max(
            float(
                available_width
                if available_width is not None
                else cls.DEFAULT_WORD_AVAILABLE_WIDTH
            ),
            cls.MINIMUM_RENDERED_COLUMN_WIDTH,
        )

        if (
            table.disposition
            == EditableTableDisposition.SKIP
        ):
            report.decision = (
                EditableTableRenderDecision.SKIP
            )

            report.set_confidence(
                0.0
            )

            report.add_issue(
                code="TABLE_MARKED_SKIP",
                message=(
                    "The upstream table model requested that "
                    "this table be skipped."
                ),
                severity=(
                    EditableTableValidationSeverity
                    .INFO
                ),
            )

            cls._record_metrics(
                table=table,
                report=report,
                available_width=(
                    resolved_available_width
                ),
            )

            return report

        cls._validate_table_dimensions(
            table=table,
            report=report,
        )

        row_geometry_score = (
            cls._validate_rows(
                table=table,
                report=report,
            )
        )

        column_geometry_score = (
            cls._validate_columns(
                table=table,
                report=report,
                available_width=(
                    resolved_available_width
                ),
            )
        )

        ownership_score = (
            cls._validate_grid_ownership(
                table=table,
                report=report,
            )
        )

        content_score = (
            cls._validate_content(
                table=table,
                report=report,
            )
        )

        merge_score = (
            cls._validate_merges(
                table=table,
                report=report,
            )
        )

        style_score = (
            cls._validate_styles(
                table=table,
                report=report,
            )
        )

        reconstruction_score = (
            cls._validate_reconstruction(
                table=table,
                report=report,
            )
        )

        cls._validate_unsupported_features(
            table=table,
            report=report,
        )

        geometry_score = mean(
            [
                row_geometry_score,
                column_geometry_score,
            ]
        )

        structure_score = (
            ownership_score
        )

        native_confidence = (
            0.35 * structure_score
            + 0.20 * geometry_score
            + 0.15 * content_score
            + 0.10 * merge_score
            + 0.10 * style_score
            + 0.10 * reconstruction_score
        )

        # Existing table confidence is supporting evidence, not
        # the sole authority.
        native_confidence = (
            0.85 * native_confidence
            + 0.15 * clamp_confidence(
                table.confidence
            )
        )

        report.set_confidence(
            native_confidence
        )

        cls._record_metrics(
            table=table,
            report=report,
            available_width=(
                resolved_available_width
            ),
            structure_score=(
                structure_score
            ),
            geometry_score=(
                geometry_score
            ),
            content_score=(
                content_score
            ),
            merge_score=(
                merge_score
            ),
            style_score=(
                style_score
            ),
            reconstruction_score=(
                reconstruction_score
            ),
        )

        cls._resolve_decision(
            table=table,
            report=report,
        )

        return report

    # ---------------------------------------------------------
    # Table dimensions and row/column geometry
    # ---------------------------------------------------------

    @classmethod
    def _validate_table_dimensions(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> None:
        if float(
            table.width
        ) <= 0.0:
            report.add_issue(
                code="NON_POSITIVE_TABLE_WIDTH",
                message=(
                    "The table rectangle does not have a "
                    "positive width."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        if float(
            table.height
        ) <= 0.0:
            report.add_issue(
                code="NON_POSITIVE_TABLE_HEIGHT",
                message=(
                    "The table rectangle does not have a "
                    "positive height."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        if table.row_count < 1:
            report.add_issue(
                code="INVALID_ROW_COUNT",
                message=(
                    "The table row count must be positive."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        if table.column_count < 1:
            report.add_issue(
                code="INVALID_COLUMN_COUNT",
                message=(
                    "The table column count must be positive."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        if (
            table.column_count
            > cls.MAXIMUM_NATIVE_COLUMNS
        ):
            report.add_issue(
                code="WORD_COLUMN_LIMIT_EXCEEDED",
                message=(
                    "The table exceeds the supported native "
                    "Word column count."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        if (
            table.row_count
            > cls.MAXIMUM_NATIVE_ROWS
        ):
            report.add_issue(
                code="NATIVE_ROW_LIMIT_EXCEEDED",
                message=(
                    "The table is too large for reliable "
                    "native rendering in one Word table."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

    @classmethod
    def _validate_rows(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        if (
            len(table.rows)
            != table.row_count
        ):
            report.add_issue(
                code="INCOMPLETE_ROW_DEFINITIONS",
                message=(
                    "The number of row definitions does not "
                    "match the logical row count."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        rows_by_index: dict[
            int,
            Any,
        ] = {}

        duplicate_indexes: set[int] = set()

        for row in table.rows:
            if row.row_index in rows_by_index:
                duplicate_indexes.add(
                    row.row_index
                )

            rows_by_index[
                row.row_index
            ] = row

        for row_index in sorted(
            duplicate_indexes
        ):
            report.add_issue(
                code="DUPLICATE_ROW_INDEX",
                message=(
                    "More than one row definition uses the "
                    "same row index."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
                row_index=row_index,
            )

        valid_segments = 0

        previous_bottom = None

        for row_index in range(
            table.row_count
        ):
            row = rows_by_index.get(
                row_index
            )

            if row is None:
                continue

            top = float(
                row.top
            )

            bottom = float(
                row.bottom
            )

            if (
                not math.isfinite(top)
                or not math.isfinite(bottom)
            ):
                report.add_issue(
                    code="NON_FINITE_ROW_GEOMETRY",
                    message=(
                        "A row contains non-finite geometry."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=row_index,
                )

                continue

            if (
                bottom - top
                <= 0.0
            ):
                report.add_issue(
                    code="NON_POSITIVE_ROW_HEIGHT",
                    message=(
                        "A row does not have a positive height."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=row_index,
                )

                continue

            if (
                top
                < float(table.bbox.top)
                - cls.GEOMETRY_TOLERANCE
                or bottom
                > float(table.bbox.bottom)
                + cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="ROW_OUTSIDE_TABLE_BOUNDS",
                    message=(
                        "A row extends materially outside the "
                        "table rectangle."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=row_index,
                )

            if (
                previous_bottom is not None
                and top
                < previous_bottom
                - cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="NON_MONOTONIC_ROW_GEOMETRY",
                    message=(
                        "Row geometry overlaps or is not ordered "
                        "from top to bottom."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=row_index,
                )

            if (
                previous_bottom is not None
                and abs(
                    top - previous_bottom
                )
                > cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="ROW_BOUNDARY_GAP",
                    message=(
                        "Adjacent row definitions do not share "
                        "a continuous boundary."
                    ),
                    severity=(
                        EditableTableValidationSeverity.WARNING
                    ),
                    row_index=row_index,
                )

            previous_bottom = bottom

            valid_segments += 1

        return clamp_confidence(
            valid_segments
            / max(
                table.row_count,
                1,
            )
            - 0.12 * len(
                [
                    issue
                    for issue in report.errors
                    if (
                        issue.code
                        in {
                            "INCOMPLETE_ROW_DEFINITIONS",
                            "DUPLICATE_ROW_INDEX",
                            "NON_FINITE_ROW_GEOMETRY",
                            "NON_POSITIVE_ROW_HEIGHT",
                            "ROW_OUTSIDE_TABLE_BOUNDS",
                            "NON_MONOTONIC_ROW_GEOMETRY",
                        }
                    )
                ]
            )
        )

    @classmethod
    def _validate_columns(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
        available_width: float,
    ) -> float:
        if (
            len(table.columns)
            != table.column_count
        ):
            report.add_issue(
                code="INCOMPLETE_COLUMN_DEFINITIONS",
                message=(
                    "The number of column definitions does not "
                    "match the logical column count."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        columns_by_index: dict[
            int,
            Any,
        ] = {}

        duplicate_indexes: set[int] = set()

        for column in table.columns:
            if (
                column.column_index
                in columns_by_index
            ):
                duplicate_indexes.add(
                    column.column_index
                )

            columns_by_index[
                column.column_index
            ] = column

        for column_index in sorted(
            duplicate_indexes
        ):
            report.add_issue(
                code="DUPLICATE_COLUMN_INDEX",
                message=(
                    "More than one column definition uses the "
                    "same column index."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
                column_index=column_index,
            )

        valid_segments = 0

        previous_right = None

        source_widths: list[float] = []

        for column_index in range(
            table.column_count
        ):
            column = columns_by_index.get(
                column_index
            )

            if column is None:
                continue

            left = float(
                column.left
            )

            right = float(
                column.right
            )

            if (
                not math.isfinite(left)
                or not math.isfinite(right)
            ):
                report.add_issue(
                    code="NON_FINITE_COLUMN_GEOMETRY",
                    message=(
                        "A column contains non-finite geometry."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    column_index=column_index,
                )

                continue

            width = right - left

            source_widths.append(
                max(
                    width,
                    0.0,
                )
            )

            if width <= 0.0:
                report.add_issue(
                    code="NON_POSITIVE_COLUMN_WIDTH",
                    message=(
                        "A column does not have a positive width."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    column_index=column_index,
                )

                continue

            if (
                left
                < float(table.bbox.left)
                - cls.GEOMETRY_TOLERANCE
                or right
                > float(table.bbox.right)
                + cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="COLUMN_OUTSIDE_TABLE_BOUNDS",
                    message=(
                        "A column extends materially outside the "
                        "table rectangle."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    column_index=column_index,
                )

            if (
                previous_right is not None
                and left
                < previous_right
                - cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="NON_MONOTONIC_COLUMN_GEOMETRY",
                    message=(
                        "Column geometry overlaps or is not "
                        "ordered from left to right."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    column_index=column_index,
                )

            if (
                previous_right is not None
                and abs(
                    left - previous_right
                )
                > cls.GEOMETRY_TOLERANCE
            ):
                report.add_issue(
                    code="COLUMN_BOUNDARY_GAP",
                    message=(
                        "Adjacent column definitions do not "
                        "share a continuous boundary."
                    ),
                    severity=(
                        EditableTableValidationSeverity.WARNING
                    ),
                    column_index=column_index,
                )

            previous_right = right

            valid_segments += 1

        source_total = sum(
            source_widths
        )

        if (
            source_total > 0.0
            and source_widths
        ):
            target_width = min(
                source_total,
                available_width,
            )

            scale = (
                target_width
                / source_total
            )

            rendered_widths = [
                width * scale
                for width in source_widths
            ]

            for column_index, rendered_width in enumerate(
                rendered_widths
            ):
                if (
                    rendered_width
                    < cls.MINIMUM_RENDERED_COLUMN_WIDTH
                ):
                    report.add_issue(
                        code="RENDERED_COLUMN_TOO_NARROW",
                        message=(
                            "Proportional Word scaling would "
                            "produce an unusably narrow column."
                        ),
                        severity=(
                            EditableTableValidationSeverity
                            .ERROR
                        ),
                        column_index=column_index,
                    )

        return clamp_confidence(
            valid_segments
            / max(
                table.column_count,
                1,
            )
            - 0.12 * len(
                [
                    issue
                    for issue in report.errors
                    if (
                        issue.code
                        in {
                            "INCOMPLETE_COLUMN_DEFINITIONS",
                            "DUPLICATE_COLUMN_INDEX",
                            "NON_FINITE_COLUMN_GEOMETRY",
                            "NON_POSITIVE_COLUMN_WIDTH",
                            "COLUMN_OUTSIDE_TABLE_BOUNDS",
                            "NON_MONOTONIC_COLUMN_GEOMETRY",
                            "RENDERED_COLUMN_TOO_NARROW",
                        }
                    )
                ]
            )
        )

    # ---------------------------------------------------------
    # Grid ownership
    # ---------------------------------------------------------

    @classmethod
    def _validate_grid_ownership(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        owners: dict[
            tuple[int, int],
            list[Any],
        ] = {}

        anchors: set[
            tuple[int, int]
        ] = set()

        duplicate_anchor_count = 0

        invalid_span_count = 0

        for cell in table.cells:
            anchor = (
                int(
                    cell.row_index
                ),
                int(
                    cell.column_index
                ),
            )

            if anchor in anchors:
                duplicate_anchor_count += 1

                report.add_issue(
                    code="DUPLICATE_CELL_ANCHOR",
                    message=(
                        "More than one cell uses the same grid "
                        "anchor."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=anchor[0],
                    column_index=anchor[1],
                )

            anchors.add(
                anchor
            )

            row_span = int(
                cell.row_span
            )

            column_span = int(
                cell.column_span
            )

            if (
                anchor[0] < 0
                or anchor[1] < 0
                or row_span < 1
                or column_span < 1
                or anchor[0] + row_span
                > table.row_count
                or anchor[1] + column_span
                > table.column_count
            ):
                invalid_span_count += 1

                report.add_issue(
                    code="CELL_SPAN_OUTSIDE_GRID",
                    message=(
                        "A cell anchor or span extends outside "
                        "the logical table grid."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=anchor[0],
                    column_index=anchor[1],
                )

                continue

            for row_index in range(
                anchor[0],
                anchor[0] + row_span,
            ):
                for column_index in range(
                    anchor[1],
                    anchor[1]
                    + column_span,
                ):
                    owners.setdefault(
                        (
                            row_index,
                            column_index,
                        ),
                        [],
                    ).append(
                        cell
                    )

        expected_positions = {
            (
                row_index,
                column_index,
            )
            for row_index in range(
                table.row_count
            )
            for column_index in range(
                table.column_count
            )
        }

        missing_positions = sorted(
            expected_positions
            - set(
                owners
            )
        )

        for row_index, column_index in (
            missing_positions
        ):
            report.add_issue(
                code="UNCOVERED_GRID_POSITION",
                message=(
                    "No cell owns an expected table-grid "
                    "position."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
                row_index=row_index,
                column_index=column_index,
            )

        overlapping_positions = sorted(
            position
            for position, cells in owners.items()
            if len(cells) > 1
        )

        for row_index, column_index in (
            overlapping_positions
        ):
            report.add_issue(
                code="OVERLAPPING_GRID_OWNERSHIP",
                message=(
                    "More than one anchor cell owns the same "
                    "table-grid position."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
                row_index=row_index,
                column_index=column_index,
            )

        owned_once = sum(
            1
            for position in expected_positions
            if len(
                owners.get(
                    position,
                    [],
                )
            )
            == 1
        )

        return clamp_confidence(
            owned_once
            / max(
                len(
                    expected_positions
                ),
                1,
            )
            - 0.10
            * duplicate_anchor_count
            - 0.10
            * invalid_span_count
        )

    # ---------------------------------------------------------
    # Content, merge, style and reconstruction evidence
    # ---------------------------------------------------------

    @classmethod
    def _validate_content(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        valid_cells = 0

        invalid_cells = 0

        paragraph_region_owners: dict[
            int,
            set[
                tuple[int, int]
            ],
        ] = {}

        for cell in table.cells:
            anchor = (
                int(
                    cell.row_index
                ),
                int(
                    cell.column_index
                ),
            )

            cell_is_valid = True

            if not isinstance(
                cell.text,
                str,
            ):
                cell_is_valid = False

                report.add_issue(
                    code="INVALID_CELL_TEXT_TYPE",
                    message=(
                        "Cell text is not represented as a "
                        "string."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=anchor[0],
                    column_index=anchor[1],
                )

            if (
                cell.is_synthetic
                and cls._cell_has_content(
                    cell
                )
            ):
                cell_is_valid = False

                report.add_issue(
                    code="SYNTHETIC_CELL_HAS_CONTENT",
                    message=(
                        "A reconstructed synthetic blank cell "
                        "unexpectedly contains content."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=anchor[0],
                    column_index=anchor[1],
                )

            for paragraph in (
                cell.content_paragraphs
                or []
            ):
                if not isinstance(
                    getattr(
                        paragraph,
                        "text",
                        None,
                    ),
                    str,
                ):
                    cell_is_valid = False

                    report.add_issue(
                        code="INVALID_CELL_PARAGRAPH_TEXT",
                        message=(
                            "A table-cell paragraph does not "
                            "contain valid string text."
                        ),
                        severity=(
                            EditableTableValidationSeverity.ERROR
                        ),
                        row_index=anchor[0],
                        column_index=anchor[1],
                    )

                for run in getattr(
                    paragraph,
                    "runs",
                    [],
                ) or []:
                    if not isinstance(
                        getattr(
                            run,
                            "text",
                            None,
                        ),
                        str,
                    ):
                        cell_is_valid = False

                        report.add_issue(
                            code="INVALID_CELL_RUN_TEXT",
                            message=(
                                "A formatted table-cell run does "
                                "not contain valid string text."
                            ),
                            severity=(
                                EditableTableValidationSeverity
                                .ERROR
                            ),
                            row_index=anchor[0],
                            column_index=anchor[1],
                        )

            for region_number in (
                cell.paragraph_region_numbers
                or []
            ):
                paragraph_region_owners.setdefault(
                    int(
                        region_number
                    ),
                    set(),
                ).add(
                    anchor
                )

            if cell_is_valid:
                valid_cells += 1
            else:
                invalid_cells += 1

        for (
            region_number,
            owner_anchors,
        ) in paragraph_region_owners.items():
            if len(
                owner_anchors
            ) <= 1:
                continue

            report.add_issue(
                code="PARAGRAPH_REGION_MULTI_CELL_OWNERSHIP",
                message=(
                    "One source paragraph region is assigned "
                    "to multiple unrelated table cells."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        return clamp_confidence(
            valid_cells
            / max(
                len(
                    table.cells
                ),
                1,
            )
            - 0.10
            * invalid_cells
        )

    @classmethod
    def _validate_merges(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        merged_cells = [
            cell
            for cell in table.cells
            if (
                cell.row_span > 1
                or cell.column_span > 1
            )
        ]

        if not merged_cells:
            return 1.0

        valid_merge_count = 0

        for cell in merged_cells:
            if (
                cell.row_index
                + cell.row_span
                > table.row_count
                or cell.column_index
                + cell.column_span
                > table.column_count
            ):
                report.add_issue(
                    code="MERGE_OUTSIDE_GRID",
                    message=(
                        "A merged-cell span extends outside the "
                        "logical table grid."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                )

                continue

            if (
                cell.merge_inferred
                and float(
                    cell.merge_confidence
                )
                < cls
                .MINIMUM_NATIVE_INFERRED_MERGE_CONFIDENCE
            ):
                report.add_issue(
                    code="WEAK_INFERRED_MERGE",
                    message=(
                        "An inferred merged-cell span does not "
                        "have sufficient confidence for native "
                        "Word rendering."
                    ),
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                )

                continue

            valid_merge_count += 1

        return clamp_confidence(
            valid_merge_count
            / max(
                len(
                    merged_cells
                ),
                1,
            )
        )

    @classmethod
    def _validate_styles(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        valid_edges = 0

        total_edges = 0

        for cell in table.cells:
            for border in {
                "top": cell.borders.top,
                "right": cell.borders.right,
                "bottom": cell.borders.bottom,
                "left": cell.borders.left,
            }.values():
                total_edges += 1

                if (
                    border.style
                    not in cls.SUPPORTED_BORDER_STYLES
                ):
                    report.add_issue(
                        code="UNSUPPORTED_BORDER_STYLE",
                        message=(
                            "A cell uses a border style that "
                            "the native Word renderer does not "
                            "support."
                        ),
                        severity=(
                            EditableTableValidationSeverity.ERROR
                        ),
                        row_index=cell.row_index,
                        column_index=cell.column_index,
                    )

                    continue

                if (
                    not math.isfinite(
                        float(
                            border.width
                        )
                    )
                    or float(
                        border.width
                    )
                    < 0.0
                ):
                    report.add_issue(
                        code="INVALID_BORDER_WIDTH",
                        message=(
                            "A cell border has invalid width "
                            "metadata."
                        ),
                        severity=(
                            EditableTableValidationSeverity.ERROR
                        ),
                        row_index=cell.row_index,
                        column_index=cell.column_index,
                    )

                    continue

                valid_edges += 1

        if total_edges == 0:
            return 1.0

        return clamp_confidence(
            valid_edges
            / total_edges
        )

    @classmethod
    def _validate_reconstruction(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> float:
        grid_position_count = max(
            table.row_count
            * table.column_count,
            1,
        )

        synthetic_cells = [
            cell
            for cell in table.cells
            if cell.is_synthetic
        ]

        synthetic_position_count = sum(
            len(
                cell.covered_positions
            )
            for cell in synthetic_cells
        )

        synthetic_ratio = min(
            synthetic_position_count
            / grid_position_count,
            1.0,
        )

        if (
            synthetic_ratio
            > cls
            .MAXIMUM_NATIVE_SYNTHETIC_RATIO
        ):
            report.add_issue(
                code="EXCESSIVE_SYNTHETIC_RECONSTRUCTION",
                message=(
                    "Too much of the logical table grid was "
                    "synthesized for reliable native rendering."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        elif synthetic_ratio > 0.0:
            severity = (
                EditableTableValidationSeverity
                .WARNING
            )

            code = (
                "ELEVATED_SYNTHETIC_RECONSTRUCTION"
                if synthetic_ratio
                > cls.WARNING_SYNTHETIC_RATIO
                else "MINOR_SYNTHETIC_RECONSTRUCTION"
            )

            report.add_issue(
                code=code,
                message=(
                    "The native table contains reconstructed "
                    "blank grid positions."
                ),
                severity=severity,
            )

        return clamp_confidence(
            1.0 - synthetic_ratio
        )

    @classmethod
    def _validate_unsupported_features(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> None:
        source_table = table.source_table

        rotation = cls._resolve_rotation(
            source_table
        )

        if (
            rotation is not None
            and abs(
                rotation % 360.0
            )
            > cls.GEOMETRY_TOLERANCE
            and abs(
                rotation % 360.0
                - 360.0
            )
            > cls.GEOMETRY_TOLERANCE
        ):
            report.add_issue(
                code="ROTATED_TABLE_UNSUPPORTED",
                message=(
                    "The source table uses rotation that is not "
                    "supported by the native Word-table renderer."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

        for attribute_name, issue_code, message in (
            (
                "has_diagonal_borders",
                "DIAGONAL_BORDERS_UNSUPPORTED",
                (
                    "The source table contains diagonal "
                    "borders."
                ),
            ),
            (
                "has_non_rectangular_cells",
                "NON_RECTANGULAR_CELLS_UNSUPPORTED",
                (
                    "The source table contains non-rectangular "
                    "cells."
                ),
            ),
            (
                "has_nested_tables",
                "NESTED_TABLES_UNSUPPORTED",
                (
                    "The source table contains nested "
                    "independent table grids."
                ),
            ),
            (
                "has_vertical_text",
                "VERTICAL_TEXT_UNSUPPORTED",
                (
                    "The source table contains vertical cell "
                    "text."
                ),
            ),
        ):
            if bool(
                getattr(
                    source_table,
                    attribute_name,
                    False,
                )
            ):
                report.add_issue(
                    code=issue_code,
                    message=message,
                    severity=(
                        EditableTableValidationSeverity.ERROR
                    ),
                )

    # ---------------------------------------------------------
    # Final decision and metrics
    # ---------------------------------------------------------

    @classmethod
    def _resolve_decision(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
    ) -> None:
        if report.errors:
            report.decision = (
                EditableTableRenderDecision
                .VISUAL_FALLBACK
            )

            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            return

        if (
            table.disposition
            == EditableTableDisposition
            .VISUAL_FALLBACK
        ):
            report.add_issue(
                code="UPSTREAM_VISUAL_FALLBACK",
                message=(
                    "An upstream table-analysis stage retained "
                    "the table as visual fallback."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

            report.decision = (
                EditableTableRenderDecision
                .VISUAL_FALLBACK
            )

            return

        if (
            report.native_confidence
            < cls.MINIMUM_NATIVE_CONFIDENCE
        ):
            report.add_issue(
                code="NATIVE_CONFIDENCE_BELOW_THRESHOLD",
                message=(
                    "The combined native-render confidence is "
                    "below the accepted threshold."
                ),
                severity=(
                    EditableTableValidationSeverity.ERROR
                ),
            )

            report.decision = (
                EditableTableRenderDecision
                .VISUAL_FALLBACK
            )

            table.disposition = (
                EditableTableDisposition
                .VISUAL_FALLBACK
            )

            return

        table.disposition = (
            EditableTableDisposition.EDITABLE
        )

        if report.warnings:
            report.decision = (
                EditableTableRenderDecision
                .NATIVE_WITH_WARNINGS
            )

        elif (
            report.native_confidence
            >= cls.NATIVE_SAFE_CONFIDENCE
        ):
            report.decision = (
                EditableTableRenderDecision
                .NATIVE_SAFE
            )

        else:
            report.decision = (
                EditableTableRenderDecision
                .NATIVE_WITH_WARNINGS
            )

            report.add_issue(
                code="MODERATE_NATIVE_CONFIDENCE",
                message=(
                    "The table is natively renderable, but the "
                    "combined confidence is below the preferred "
                    "safe threshold."
                ),
                severity=(
                    EditableTableValidationSeverity.WARNING
                ),
            )

    @classmethod
    def _record_metrics(
        cls,
        *,
        table: EditableTable,
        report: EditableTableValidationReport,
        available_width: float,
        structure_score: float | None = None,
        geometry_score: float | None = None,
        content_score: float | None = None,
        merge_score: float | None = None,
        style_score: float | None = None,
        reconstruction_score: float | None = None,
    ) -> None:
        real_cells = [
            cell
            for cell in table.cells
            if not cell.is_synthetic
        ]

        synthetic_cells = [
            cell
            for cell in table.cells
            if cell.is_synthetic
        ]

        merged_cells = [
            cell
            for cell in table.cells
            if (
                cell.row_span > 1
                or cell.column_span > 1
            )
        ]

        inferred_merges = [
            cell
            for cell in merged_cells
            if cell.merge_inferred
        ]

        grid_position_count = max(
            table.row_count
            * table.column_count,
            1,
        )

        synthetic_position_count = sum(
            len(
                cell.covered_positions
            )
            for cell in synthetic_cells
        )

        report.set_metric(
            "row_count",
            table.row_count,
        )

        report.set_metric(
            "column_count",
            table.column_count,
        )

        report.set_metric(
            "anchor_cell_count",
            len(
                table.cells
            ),
        )

        report.set_metric(
            "grid_position_count",
            grid_position_count,
        )

        report.set_metric(
            "real_cell_count",
            len(
                real_cells
            ),
        )

        report.set_metric(
            "synthetic_cell_count",
            len(
                synthetic_cells
            ),
        )

        report.set_metric(
            "synthetic_ratio",
            synthetic_position_count
            / grid_position_count,
        )

        report.set_metric(
            "merged_cell_count",
            len(
                merged_cells
            ),
        )

        report.set_metric(
            "inferred_merge_count",
            len(
                inferred_merges
            ),
        )

        report.set_metric(
            "minimum_row_height",
            min(
                [
                    float(
                        row.height
                    )
                    for row in table.rows
                ]
                or [
                    0.0
                ]
            ),
        )

        report.set_metric(
            "minimum_column_width",
            min(
                [
                    float(
                        column.width
                    )
                    for column in table.columns
                ]
                or [
                    0.0
                ]
            ),
        )

        report.set_metric(
            "table_width",
            float(
                table.width
            ),
        )

        report.set_metric(
            "table_height",
            float(
                table.height
            ),
        )

        report.set_metric(
            "available_width",
            float(
                available_width
            ),
        )

        for name, value in (
            (
                "structure_score",
                structure_score,
            ),
            (
                "geometry_score",
                geometry_score,
            ),
            (
                "content_score",
                content_score,
            ),
            (
                "merge_score",
                merge_score,
            ),
            (
                "style_score",
                style_score,
            ),
            (
                "reconstruction_score",
                reconstruction_score,
            ),
        ):
            if value is not None:
                report.set_metric(
                    name,
                    clamp_confidence(
                        value
                    ),
                )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @classmethod
    def _resolve_available_width(
        cls,
        page,
    ) -> float:
        bbox = getattr(
            page,
            "bbox",
            None,
        )

        page_width = getattr(
            bbox,
            "width",
            None,
        )

        try:
            resolved_page_width = float(
                page_width
            )

        except (
            TypeError,
            ValueError,
        ):
            return cls.DEFAULT_WORD_AVAILABLE_WIDTH

        return max(
            resolved_page_width
            - 2.0
            * cls.DEFAULT_PAGE_MARGIN,
            cls.MINIMUM_RENDERED_COLUMN_WIDTH,
        )

    @staticmethod
    def _cell_has_content(
        cell,
    ) -> bool:
        if isinstance(
            cell.text,
            str,
        ) and cell.text.strip():
            return True

        return any(
            isinstance(
                getattr(
                    paragraph,
                    "text",
                    None,
                ),
                str,
            )
            and getattr(
                paragraph,
                "text",
                "",
            ).strip()
            for paragraph in (
                cell.content_paragraphs
                or []
            )
        )

    @staticmethod
    def _resolve_rotation(
        source_table,
    ) -> float | None:
        if source_table is None:
            return None

        for attribute_name in (
            "rotation",
            "angle",
            "rotate",
            "text_rotation",
        ):
            value = getattr(
                source_table,
                attribute_name,
                None,
            )

            if value is None:
                continue

            try:
                return float(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return None
