from __future__ import annotations

import json

from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.models.alignment_validation import (
    AlignmentValidationReport,
)


class AlignmentValidationReportWriter:
    """
    Writes an AlignmentValidationReport to JSON.
    """

    @classmethod
    def write(
        cls,
        report: AlignmentValidationReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(
            output_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        serialized_report = (
            cls._serialize(
                report
            )
        )

        with path.open(
            mode="w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                serialized_report,
                output_file,
                ensure_ascii=False,
                indent=2,
            )

        return path

    @classmethod
    def _serialize(
        cls,
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            Enum,
        ):
            return value.value

        if is_dataclass(
            value
        ):
            return {
                field_definition.name: (
                    cls._serialize(
                        getattr(
                            value,
                            field_definition.name,
                        )
                    )
                )
                for field_definition
                in fields(value)
            }

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): cls._serialize(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                cls._serialize(
                    item
                )
                for item in value
            ]

        return value