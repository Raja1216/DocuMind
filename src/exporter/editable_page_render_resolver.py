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


class EditableRenderAction(
    str,
    Enum,
):
    """
    Action that the editable DOCX exporter should perform for
    one unified render-plan item.
    """

    RENDER_PARAGRAPH = "render_paragraph"

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

        action_map = {
            RenderItemKind.TABLE: (
                EditableRenderAction.DEFER_TABLE
            ),

            RenderItemKind.IMAGE: (
                EditableRenderAction.DEFER_IMAGE
            ),

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