from __future__ import annotations

from typing import Any

from src.exporter.editable_table_region_fallback_renderer import (
    EditableTableRegionFallbackRenderer,
)
from src.exporter.editable_word_table_renderer import (
    EditableWordTableRenderer,
)
from src.models.editable_table_export import (
    EditableTableExportMode,
    EditableTableExportResult,
)
from src.models.editable_table_validation import (
    EditableTableRenderDecision,
    EditableTableValidationSeverity,
)


class EditableTableExportCoordinator:
    """
    Safely export one table without allowing a malformed table to
    stop the entire document conversion.

    Native rendering is transactional at the Word-body level. Any
    partially inserted XML is removed before visual fallback runs.
    """

    @classmethod
    def render(
        cls,
        *,
        container,
        page,
        table,
        available_width: float,
        prefer_native: bool,
        validation_report=None,
    ) -> EditableTableExportResult:
        requested_mode = (
            EditableTableExportMode.NATIVE
            if prefer_native
            else EditableTableExportMode
            .VISUAL_FALLBACK
        )

        result = EditableTableExportResult(
            table_id=str(
                getattr(
                    table,
                    "table_id",
                    "",
                )
            ),
            page_number=max(
                int(
                    getattr(
                        table,
                        "page_number",
                        getattr(
                            page,
                            "number",
                            1,
                        ),
                    )
                ),
                1,
            ),
            requested_mode=requested_mode,
        )

        if prefer_native:
            result.native_attempted = True

            native_snapshot = (
                cls._snapshot_container(
                    container
                )
            )

            try:
                EditableWordTableRenderer.render(
                    container=container,
                    table=table,
                    available_width=available_width,
                )

                result.final_mode = (
                    EditableTableExportMode.NATIVE
                )
                result.success = True

                cls._store_result(
                    page=page,
                    result=result,
                )

                return result

            except Exception as error:
                cls._rollback_container(
                    container=container,
                    snapshot=native_snapshot,
                )

                result.native_error = (
                    cls._format_error(
                        error
                    )
                )

                result.add_warning(
                    (
                        "Native Word-table rendering failed; "
                        "the source-region fallback was attempted."
                    )
                )

                cls._record_validation_issue(
                    validation_report=validation_report,
                    code="NATIVE_RENDER_EXCEPTION",
                    message=(
                        "Native Word-table rendering failed at "
                        f"runtime: {result.native_error}"
                    ),
                    severity=(
                        EditableTableValidationSeverity
                        .WARNING
                    ),
                )

        result.fallback_attempted = True

        fallback_snapshot = (
            cls._snapshot_container(
                container
            )
        )

        try:
            (
                _,
                _,
                rendered_width,
                rendered_height,
            ) = (
                EditableTableRegionFallbackRenderer
                .render(
                    container=container,
                    page=page,
                    table=table,
                    available_width=available_width,
                )
            )

            result.final_mode = (
                EditableTableExportMode
                .VISUAL_FALLBACK
            )
            result.success = True
            result.rendered_width = (
                rendered_width
            )
            result.rendered_height = (
                rendered_height
            )

            if validation_report is not None:
                validation_report.decision = (
                    EditableTableRenderDecision
                    .VISUAL_FALLBACK
                )

            cls._store_result(
                page=page,
                result=result,
            )

            return result

        except Exception as error:
            cls._rollback_container(
                container=container,
                snapshot=fallback_snapshot,
            )

            result.fallback_error = (
                cls._format_error(
                    error
                )
            )

            result.final_mode = (
                EditableTableExportMode.FAILED
            )
            result.success = False

            cls._record_validation_issue(
                validation_report=validation_report,
                code="TABLE_FALLBACK_RENDER_EXCEPTION",
                message=(
                    "The visual table-region fallback failed at "
                    f"runtime: {result.fallback_error}"
                ),
                severity=(
                    EditableTableValidationSeverity
                    .ERROR
                ),
            )

            cls._store_result(
                page=page,
                result=result,
            )

            return result

    @staticmethod
    def _container_parent(
        container,
    ):
        element = getattr(
            container,
            "_element",
            None,
        )

        if element is not None:
            body = getattr(
                element,
                "body",
                None,
            )

            if body is not None:
                return body

        table_cell = getattr(
            container,
            "_tc",
            None,
        )

        if table_cell is not None:
            return table_cell

        raise TypeError(
            "The Word container does not expose a rollback-capable XML parent."
        )

    @classmethod
    def _snapshot_container(
        cls,
        container,
    ) -> set[int]:
        parent = cls._container_parent(
            container
        )

        return {
            id(child)
            for child in parent
        }

    @classmethod
    def _rollback_container(
        cls,
        *,
        container,
        snapshot: set[int],
    ) -> None:
        parent = cls._container_parent(
            container
        )

        for child in list(parent):
            if id(child) not in snapshot:
                parent.remove(
                    child
                )

    @staticmethod
    def _format_error(
        error: Exception,
    ) -> str:
        message = str(
            error
        ).strip()

        error_name = type(
            error
        ).__name__

        return (
            f"{error_name}: {message}"
            if message
            else error_name
        )

    @staticmethod
    def _record_validation_issue(
        *,
        validation_report,
        code: str,
        message: str,
        severity,
    ) -> None:
        if validation_report is None:
            return

        add_issue = getattr(
            validation_report,
            "add_issue",
            None,
        )

        if callable(add_issue):
            add_issue(
                code=code,
                message=message,
                severity=severity,
            )

    @staticmethod
    def _store_result(
        *,
        page,
        result: EditableTableExportResult,
    ) -> None:
        export_results = getattr(
            page,
            "editable_table_export_results",
            None,
        )

        if export_results is None:
            export_results = {}

            setattr(
                page,
                "editable_table_export_results",
                export_results,
            )

        export_results[
            result.table_id
        ] = result
