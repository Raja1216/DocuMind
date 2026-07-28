from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.exporter.editable_layout_resolver import (
    EditableLayoutResolver,
)
from src.models.page_render_plan import (
    PageRenderItem,
    RenderDisposition,
    RenderItemKind,
    RenderItemRole,
    RenderPlacement,
)
from src.models.editable_table_validation import (
    EditableTableRenderDecision,
)

from src.models.editable_image import (
    EditableImage,
    EditableImageDisposition,
    EditableImagePayloadStatus,
    EditableImagePlacement,
)


class EditableRenderAction(
    str,
    Enum,
):
    """
    Action that the editable DOCX exporter should perform for
    one unified render-plan item.
    """

    RENDER_PARAGRAPH = "render_paragraph"

    RENDER_TABLE = "render_table"

    RENDER_TABLE_FALLBACK = (
        "render_table_fallback"
    )
    
    RENDER_INLINE_IMAGE = (
        "render_inline_image"
    )
    
    RENDER_FLOATING_IMAGE = (
        "render_floating_image"
    )

    DEFER_TABLE = "defer_table"

    DEFER_IMAGE = "defer_image"

    DEFER_CHART = "defer_chart"

    DEFER_VECTOR = "defer_vector"

    DEFER_PAGE_FALLBACK = "defer_page_fallback"

    IGNORE = "ignore"


@dataclass(slots=True)
class EditableRenderInstruction:
    """
    Editable-export instruction derived from one PageRenderItem.

    `layout_item` is populated for paragraph instructions using
    the existing EditableLayoutResolver.
    """

    order: int

    action: EditableRenderAction

    source: Any

    render_item: PageRenderItem | None = None

    layout_item: Any | None = None

    reason: str = ""

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def is_paragraph(
        self,
    ) -> bool:
        return (
            self.action
            == EditableRenderAction.RENDER_PARAGRAPH
        )

    @property
    def is_table(
        self,
    ) -> bool:
        return self.action in {
            EditableRenderAction.RENDER_TABLE,
            EditableRenderAction
            .RENDER_TABLE_FALLBACK,
        }

    @property
    def is_inline_image(
        self,
    ) -> bool:
        return (
            self.action
            == EditableRenderAction
            .RENDER_INLINE_IMAGE
        )

    @property
    def is_floating_image(
        self,
    ) -> bool:
        return (
            self.action
            == EditableRenderAction
            .RENDER_FLOATING_IMAGE
        )
    
    @property
    def is_image(
        self,
    ) -> bool:
        return self.action in {
            EditableRenderAction
            .RENDER_INLINE_IMAGE,
            EditableRenderAction
            .RENDER_FLOATING_IMAGE,
        }
    
    @property
    def is_deferred(
        self,
    ) -> bool:
        return self.action in {
            EditableRenderAction.DEFER_TABLE,
            EditableRenderAction.DEFER_IMAGE,
            EditableRenderAction.DEFER_CHART,
            EditableRenderAction.DEFER_VECTOR,
            EditableRenderAction.DEFER_PAGE_FALLBACK,
        }

    @property
    def is_ignored(
        self,
    ) -> bool:
        return (
            self.action
            == EditableRenderAction.IGNORE
        )


@dataclass(slots=True)
class EditablePageRenderPlan:
    """
    Instructions consumed by DocxExporter for one PDF page.
    """

    page_number: int

    instructions: list[
        EditableRenderInstruction
    ] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def paragraph_instructions(
        self,
    ) -> list[EditableRenderInstruction]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_paragraph
        ]

    @property
    def table_instructions(
        self,
    ) -> list[EditableRenderInstruction]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_table
        ]

    @property
    def inline_image_instructions(
        self,
    ) -> list[
        EditableRenderInstruction
    ]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_inline_image
        ]

    @property
    def floating_image_instructions(
        self,
    ) -> list[
        EditableRenderInstruction
    ]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_floating_image
        ]

    @property
    def image_instructions(
        self,
    ) -> list[
        EditableRenderInstruction
    ]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_image
        ]

    @property
    def deferred_instructions(
        self,
    ) -> list[EditableRenderInstruction]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_deferred
        ]

    @property
    def ignored_instructions(
        self,
    ) -> list[EditableRenderInstruction]:
        return [
            instruction
            for instruction in self.instructions
            if instruction.is_ignored
        ]

    @property
    def instruction_count(
        self,
    ) -> int:
        return len(
            self.instructions
        )

    def add_instruction(
        self,
        instruction: EditableRenderInstruction,
    ) -> None:
        self.instructions.append(
            instruction
        )


class EditablePageRenderResolver:
    """
    Converts PageRenderPlan items into instructions understood
    by the editable DOCX exporter.

    Paragraph geometry and alignment are still supplied by the
    existing EditableLayoutResolver.
    """

    @classmethod
    def build_page_plan(
        cls,
        page,
        validation_report=None,
    ) -> EditablePageRenderPlan:
        result = EditablePageRenderPlan(
            page_number=int(
                page.number
            )
        )

        layout_items = (
            cls._collect_layout_items(
                page=page,
                validation_report=(
                    validation_report
                ),
            )
        )

        (
            layout_by_identity,
            layout_by_region_number,
        ) = cls._build_layout_indexes(
            layout_items
        )

        editable_tables = list(
            getattr(
                page,
                "editable_tables",
                [],
            )
            or []
        )
        
        editable_images = list(
            getattr(
                page,
                "editable_images",
                [],
            )
            or []
        )

        table_validation_reports = dict(
            getattr(
                page,
                "editable_table_validation_reports",
                {},
            )
            or {}
        )

        render_plan = getattr(
            page,
            "render_plan",
            None,
        )

        render_items = list(
            getattr(
                render_plan,
                "items",
                [],
            )
            or []
        )

        if not render_items:
            cls._build_legacy_fallback_plan(
                page=page,
                result=result,
                layout_items=layout_items,
            )

            return result

        for render_item in sorted(
            render_items,
            key=lambda item: (
                int(
                    item.order
                ),
                float(
                    item.top
                ),
                float(
                    item.left
                ),
                item.item_id,
            ),
        ):
            instruction = (
                cls._resolve_instruction(
                    render_item=render_item,
                    layout_by_identity=(
                        layout_by_identity
                    ),
                    layout_by_region_number=(
                        layout_by_region_number
                    ),
                    editable_tables=(
                        editable_tables
                    ),
                    editable_images=(
                        editable_images
                    ),
                    table_validation_reports=(
                        table_validation_reports
                    ),
                )
            )

            result.add_instruction(
                instruction
            )

            if instruction.warnings:
                result.warnings.extend(
                    warning
                    for warning in instruction.warnings
                    if warning
                    not in result.warnings
                )

        return result

    # ---------------------------------------------------------
    # Instruction resolution
    # ---------------------------------------------------------

    @classmethod
    def _resolve_instruction(
        cls,
        render_item: PageRenderItem,
        layout_by_identity: dict[int, Any],
        layout_by_region_number: dict[int, Any],
        editable_tables: list[Any],
        editable_images: list[
            EditableImage
        ],
        table_validation_reports: dict[str, Any],
    ) -> EditableRenderInstruction:
        source = render_item.source

        if (
            render_item.disposition
            == RenderDisposition.SKIP
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=source,
                render_item=render_item,
                reason=(
                    cls._resolve_skip_reason(
                        render_item
                    )
                ),
            )

        if render_item.kind == RenderItemKind.PARAGRAPH:
            return cls._resolve_paragraph_instruction(
                render_item=render_item,
                layout_by_identity=(
                    layout_by_identity
                ),
                layout_by_region_number=(
                    layout_by_region_number
                ),
            )

        if render_item.kind == RenderItemKind.TABLE:
            return cls._resolve_table_instruction(
                render_item=render_item,
                editable_tables=editable_tables,
                table_validation_reports=(
                    table_validation_reports
                ),
            )
        if render_item.kind == RenderItemKind.IMAGE:
            return cls._resolve_image_instruction(
                render_item=render_item,
                editable_images=editable_images,
            )
    
        action_map = {
            RenderItemKind.CHART: (
                EditableRenderAction.DEFER_CHART
            ),

            RenderItemKind.VECTOR: (
                EditableRenderAction.DEFER_VECTOR
            ),

            RenderItemKind.PAGE_FALLBACK: (
                EditableRenderAction
                .DEFER_PAGE_FALLBACK
            ),
        }

        action = action_map.get(
            render_item.kind,
            EditableRenderAction.IGNORE,
        )

        return EditableRenderInstruction(
            order=render_item.order,
            action=action,
            source=source,
            render_item=render_item,
            reason=(
                "The corresponding editable or visual "
                "renderer is not connected yet."
            ),
        )

    @classmethod
    def _resolve_image_instruction(
        cls,
        *,
        render_item: PageRenderItem,
        editable_images: list[
            EditableImage
        ],
    ) -> EditableRenderInstruction:
        """
        Resolve one unified image item into inline, floating,
        deferred or ignored output.
    
        The normalized EditableImage placement is the final image
        placement authority. The PageRenderItem still controls
        ordering and prevents background or overlay items from
        being rendered as ordinary floating images.
        """
    
        source_image = render_item.source
    
        editable_image = (
            cls._find_editable_image(
                render_item=render_item,
                editable_images=editable_images,
            )
        )
    
        if editable_image is None:
            warning = (
                "No unique normalized EditableImage model "
                f"matches {render_item.item_id}."
            )
    
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_IMAGE
                ),
                source=source_image,
                render_item=render_item,
                reason=(
                    "Image rendering requires a unique "
                    "normalized image-placement model."
                ),
                warnings=[
                    warning
                ],
            )
    
        if (
            editable_image.disposition
            == EditableImageDisposition.SKIP
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction.IGNORE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "The normalized image disposition "
                    "is SKIP."
                ),
            )
    
        if not editable_image.has_resolved_payload:
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_IMAGE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "The image has no successfully "
                    "resolved payload."
                ),
            )
    
        if (
            editable_image.payload_status
            not in {
                EditableImagePayloadStatus.READY,
                EditableImagePayloadStatus
                .REGION_RENDERED,
            }
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_IMAGE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "The image payload status is not "
                    "supported by a native renderer."
                ),
            )
    
        try:
            normalized_rotation = (
                float(
                    editable_image.rotation
                )
                % 360.0
            )
    
        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            normalized_rotation = 0.0
    
        rotation_distance = min(
            abs(
                normalized_rotation
            ),
            abs(
                360.0
                - normalized_rotation
            ),
        )
    
        if rotation_distance > 0.01:
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_IMAGE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "Rotated images require the later "
                    "image-transform renderer."
                ),
            )
    
        # -----------------------------------------------------
        # Native inline image
        # -----------------------------------------------------
    
        if (
            editable_image.placement
            == EditableImagePlacement.INLINE
        ):
            if (
                render_item.placement
                != RenderPlacement.FLOW
            ):
                return EditableRenderInstruction(
                    order=render_item.order,
                    action=(
                        EditableRenderAction
                        .DEFER_IMAGE
                    ),
                    source=editable_image,
                    render_item=render_item,
                    reason=(
                        "An inline image must participate "
                        "in normal document flow."
                    ),
                )
    
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_INLINE_IMAGE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "Render as a native inline Word image."
                ),
            )
    
        # -----------------------------------------------------
        # Native floating image
        # -----------------------------------------------------
    
        if (
            editable_image.placement
            == EditableImagePlacement.FLOATING
        ):
            if (
                render_item.placement
                in {
                    RenderPlacement.BACKGROUND,
                    RenderPlacement.OVERLAY,
                }
            ):
                return EditableRenderInstruction(
                    order=render_item.order,
                    action=(
                        EditableRenderAction
                        .DEFER_IMAGE
                    ),
                    source=editable_image,
                    render_item=render_item,
                    reason=(
                        "Background and overlay render-plan "
                        "items require dedicated image "
                        "layer renderers."
                    ),
                )
    
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_FLOATING_IMAGE
                ),
                source=editable_image,
                render_item=render_item,
                reason=(
                    "Render as a page-relative floating "
                    "Word image."
                ),
            )
    
        # -----------------------------------------------------
        # Deferred placement types
        # -----------------------------------------------------
    
        if (
            editable_image.placement
            == EditableImagePlacement.BACKGROUND
        ):
            reason = (
                "Background images require the later "
                "page-background renderer."
            )
    
        elif (
            editable_image.placement
            == EditableImagePlacement.OVERLAY
        ):
            reason = (
                "Overlay images require the later "
                "foreground-layer renderer."
            )
    
        else:
            reason = (
                "The image placement remains unresolved."
            )
    
        return EditableRenderInstruction(
            order=render_item.order,
            action=(
                EditableRenderAction.DEFER_IMAGE
            ),
            source=editable_image,
            render_item=render_item,
            reason=reason,
        )

    @classmethod
    def _resolve_table_instruction(
        cls,
        *,
        render_item: PageRenderItem,
        editable_tables: list[Any],
        table_validation_reports: dict[str, Any],
    ) -> EditableRenderInstruction:
        source_table = render_item.source

        if (
            render_item.placement
            != RenderPlacement.FLOW
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_TABLE
                ),
                source=source_table,
                render_item=render_item,
                reason=(
                    "Non-flow table placement requires the "
                    "later floating-object renderer."
                ),
            )

        editable_table = (
            cls._match_editable_table(
                render_item=render_item,
                editable_tables=editable_tables,
            )
        )

        if editable_table is None:
            warning = (
                "No normalized EditableTable model matches "
                f"{render_item.item_id}."
            )

            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_TABLE
                ),
                source=source_table,
                render_item=render_item,
                reason=(
                    "Native Word-table rendering cannot run "
                    "without a normalized table model."
                ),
                warnings=[
                    warning
                ],
            )

        validation_report = (
            table_validation_reports.get(
                str(
                    getattr(
                        editable_table,
                        "table_id",
                        "",
                    )
                )
            )
        )

        if validation_report is None:
            warning = (
                "No EditableTableValidationReport exists for "
                f"{getattr(editable_table, 'table_id', render_item.item_id)}."
            )

            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .DEFER_TABLE
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "Native Word-table rendering requires a "
                    "completed generalized validation report."
                ),
                warnings=[
                    warning
                ],
            )

        validation_decision = getattr(
            validation_report,
            "decision",
            None,
        )

        if (
            validation_decision
            == EditableTableRenderDecision.SKIP
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The table validator selected the skip "
                    "decision."
                ),
            )

        if (
            validation_decision
            == EditableTableRenderDecision
            .VISUAL_FALLBACK
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_TABLE_FALLBACK
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The generalized table validator selected "
                    "source-region visual fallback."
                ),
                warnings=[
                    issue.message
                    for issue in getattr(
                        validation_report,
                        "issues",
                        [],
                    )
                    if str(
                        getattr(
                            getattr(
                                issue,
                                "severity",
                                None,
                            ),
                            "value",
                            "",
                        )
                    )
                    in {
                        "warning",
                        "error",
                    }
                ],
            )

        if (
            render_item.disposition
            != RenderDisposition.EDITABLE
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_TABLE_FALLBACK
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The unified render plan selected a visual "
                    "table representation."
                ),
            )

        if not bool(
            getattr(
                editable_table,
                "is_editable",
                False,
            )
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_TABLE_FALLBACK
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The normalized table requested visual "
                    "fallback instead of native Word output."
                ),
            )

        if not bool(
            getattr(
                editable_table,
                "is_structurally_valid",
                False,
            )
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_TABLE_FALLBACK
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The normalized table grid is not "
                    "structurally valid."
                ),
            )

        row_count = int(
            getattr(
                editable_table,
                "row_count",
                0,
            )
        )

        column_count = int(
            getattr(
                editable_table,
                "column_count",
                0,
            )
        )

        if (
            len(
                getattr(
                    editable_table,
                    "rows",
                    [],
                )
                or []
            )
            != row_count
            or len(
                getattr(
                    editable_table,
                    "columns",
                    [],
                )
                or []
            )
            != column_count
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=(
                    EditableRenderAction
                    .RENDER_TABLE_FALLBACK
                ),
                source=editable_table,
                render_item=render_item,
                reason=(
                    "The normalized table does not have complete "
                    "row and column definitions."
                ),
            )

        return EditableRenderInstruction(
            order=render_item.order,
            action=(
                EditableRenderAction
                .RENDER_TABLE
            ),
            source=editable_table,
            render_item=render_item,
            reason=(
                "Render as a native editable Word table."
            ),
        )

    @staticmethod
    def _match_editable_table(
        *,
        render_item: PageRenderItem,
        editable_tables: list[Any],
    ) -> Any | None:
        source_table = render_item.source

        for editable_table in editable_tables:
            if (
                getattr(
                    editable_table,
                    "source_table",
                    None,
                )
                is source_table
            ):
                return editable_table

        source_index = int(
            getattr(
                render_item,
                "source_index",
                -1,
            )
        )

        if (
            0
            <= source_index
            < len(editable_tables)
        ):
            indexed_table = (
                editable_tables[
                    source_index
                ]
            )

            indexed_source = getattr(
                indexed_table,
                "source_table",
                None,
            )

            if (
                indexed_source is None
                or indexed_source
                is source_table
            ):
                return indexed_table

        return None

    @classmethod
    def _find_editable_image(
        cls,
        *,
        render_item,
        editable_images: list[
            EditableImage
        ],
    ) -> EditableImage | None:
        """
        Resolve one render-plan image item to one normalized
        image placement.

        Object identity is preferred because repeated xrefs may
        represent distinct placements.
        """

        source_image = getattr(
            render_item,
            "source",
            None,
        )

        if source_image is None:
            identity_matches = []
        
        else:
            identity_matches = [
                image
                for image in editable_images
                if image.source_image
                is source_image
            ]

        if len(
            identity_matches
        ) == 1:
            return identity_matches[0]

        render_bbox = getattr(
            render_item,
            "bbox",
            None,
        )

        if render_bbox is None:
            return None

        geometry_matches = [
            image
            for image in editable_images
            if cls._image_geometry_matches(
                image.bbox,
                render_bbox,
            )
        ]

        if len(
            geometry_matches
        ) == 1:
            return geometry_matches[0]

        source_xref = cls._positive_integer_or_none(
            getattr(
                source_image,
                "xref",
                None,
            )
        )

        if source_xref is None:
            return None

        xref_geometry_matches = [
            image
            for image in geometry_matches
            if image.xref
            == source_xref
        ]

        if len(
            xref_geometry_matches
        ) == 1:
            return xref_geometry_matches[0]

        return None


    @staticmethod
    def _image_geometry_matches(
        first_bbox,
        second_bbox,
        *,
        tolerance: float = 1.5,
    ) -> bool:
        coordinate_names = (
            "left",
            "top",
            "right",
            "bottom",
        )

        try:
            return all(
                abs(
                    float(
                        getattr(
                            first_bbox,
                            coordinate_name,
                        )
                    )
                    - float(
                        getattr(
                            second_bbox,
                            coordinate_name,
                        )
                    )
                )
                <= tolerance
                for coordinate_name
                in coordinate_names
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            return False


    @staticmethod
    def _positive_integer_or_none(
        value,
    ) -> int | None:
        try:
            normalized = int(
                value
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

        return (
            normalized
            if normalized > 0
            else None
        )

    @classmethod
    def _resolve_paragraph_instruction(
        cls,
        render_item: PageRenderItem,
        layout_by_identity: dict[int, Any],
        layout_by_region_number: dict[int, Any],
    ) -> EditableRenderInstruction:
        source = render_item.source

        if render_item.role in {
            RenderItemRole.HEADER,
            RenderItemRole.FOOTER,
        }:
            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=source,
                render_item=render_item,
                reason=(
                    "Header/footer content is rendered by the "
                    "Word section header/footer exporter."
                ),
            )

        if (
            render_item.placement
            != RenderPlacement.FLOW
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=source,
                render_item=render_item,
                reason=(
                    "Non-flow paragraph is not part of the "
                    "editable document body."
                ),
            )

        if (
            render_item.disposition
            != RenderDisposition.EDITABLE
        ):
            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=source,
                render_item=render_item,
                reason=(
                    "Paragraph is not marked for native "
                    "editable rendering."
                ),
            )

        layout_item = layout_by_identity.get(
            id(
                source
            )
        )

        if layout_item is None:
            region_number = (
                cls._resolve_region_number(
                    source
                )
            )

            if region_number is not None:
                layout_item = (
                    layout_by_region_number.get(
                        region_number
                    )
                )

        if layout_item is None:
            warning = (
                "Editable layout metadata was not found for "
                f"render item {render_item.item_id}."
            )

            return EditableRenderInstruction(
                order=render_item.order,
                action=EditableRenderAction.IGNORE,
                source=source,
                render_item=render_item,
                reason=warning,
                warnings=[
                    warning
                ],
            )

        return EditableRenderInstruction(
            order=render_item.order,
            action=(
                EditableRenderAction
                .RENDER_PARAGRAPH
            ),
            source=source,
            render_item=render_item,
            layout_item=layout_item,
        )

    # ---------------------------------------------------------
    # Existing editable layout integration
    # ---------------------------------------------------------

    @staticmethod
    def _collect_layout_items(
        page,
        validation_report=None,
    ) -> list[Any]:
        layout_plan = (
            EditableLayoutResolver
            .build_page_plan(
                page=page,
                validation_report=(
                    validation_report
                ),
            )
        )

        if layout_plan is None:
            return []

        if isinstance(
            layout_plan,
            list,
        ):
            return layout_plan

        if isinstance(
            layout_plan,
            tuple,
        ):
            return list(
                layout_plan
            )

        for attribute_name in (
            "items",
            "paragraphs",
            "instructions",
        ):
            items = getattr(
                layout_plan,
                attribute_name,
                None,
            )

            if items is not None:
                return list(
                    items
                )

        try:
            return list(
                layout_plan
            )

        except TypeError:
            return []

    @classmethod
    def _build_layout_indexes(
        cls,
        layout_items: list[Any],
    ) -> tuple[
        dict[int, Any],
        dict[int, Any],
    ]:
        by_identity: dict[int, Any] = {}

        by_region_number: dict[int, Any] = {}

        for layout_item in layout_items:
            paragraph = (
                cls._resolve_layout_paragraph(
                    layout_item
                )
            )

            if paragraph is None:
                continue

            by_identity[
                id(
                    paragraph
                )
            ] = layout_item

            region_number = (
                cls._resolve_region_number(
                    paragraph
                )
            )

            if region_number is not None:
                by_region_number[
                    region_number
                ] = layout_item

        return (
            by_identity,
            by_region_number,
        )

    @staticmethod
    def _resolve_layout_paragraph(
        layout_item: Any,
    ) -> Any | None:
        for attribute_name in (
            "paragraph",
            "paragraph_region",
            "region",
            "source",
        ):
            value = getattr(
                layout_item,
                attribute_name,
                None,
            )

            if value is not None:
                return value

        return None

    # ---------------------------------------------------------
    # Legacy fallback
    # ---------------------------------------------------------

    @classmethod
    def _build_legacy_fallback_plan(
        cls,
        page,
        result: EditablePageRenderPlan,
        layout_items: list[Any],
    ) -> None:
        """
        Preserve backward compatibility when an old analyzed
        document has no unified render plan.
        """

        for order, layout_item in enumerate(
            layout_items,
            start=1,
        ):
            paragraph = (
                cls._resolve_layout_paragraph(
                    layout_item
                )
            )

            if paragraph is None:
                continue

            if getattr(
                paragraph,
                "is_list_marker_only",
                False,
            ):
                continue

            result.add_instruction(
                EditableRenderInstruction(
                    order=order,
                    action=(
                        EditableRenderAction
                        .RENDER_PARAGRAPH
                    ),
                    source=paragraph,
                    layout_item=layout_item,
                    reason=(
                        "Legacy fallback: page has no unified "
                        "render-plan items."
                    ),
                )
            )

        if layout_items:
            result.warnings.append(
                (
                    "Page used the legacy editable-layout "
                    "fallback because its unified render plan "
                    "was empty."
                )
            )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _resolve_region_number(
        source: Any,
    ) -> int | None:
        for attribute_name in (
            "region_number",
            "paragraph_region_number",
            "id",
        ):
            value = getattr(
                source,
                attribute_name,
                None,
            )

            if value is None:
                continue

            try:
                return int(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    @staticmethod
    def _resolve_skip_reason(
        render_item: PageRenderItem,
    ) -> str:
        if render_item.reasons:
            return " ".join(
                render_item.reasons
            )

        return (
            "The unified page render plan marked this item "
            "as skipped."
        )