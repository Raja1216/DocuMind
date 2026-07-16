from __future__ import annotations

from src.models.line import Line


class LineReconstructor:
    """
    Reconstruct logical paragraph text from PDF lines.
    Version 1:
    - Join wrapped lines with spaces.
    """

    @staticmethod
    def reconstruct(lines: list[Line]) -> str:

        result: list[str] = []

        for line in lines:

            line_text = "".join(
                span.text
                for span in line.spans
            ).strip()

            if not line_text:
                continue

            result.append(line_text)

        return " ".join(result)