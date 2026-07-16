from __future__ import annotations

from src.models.line import Line
from src.models.text_run import TextRun


class RunBuilder:
    """
    Convert PDF spans into logical Word runs.
    """

    @staticmethod
    def build(line: Line) -> list[TextRun]:

        runs: list[TextRun] = []

        current: TextRun | None = None

        for span in line.spans:

            # Skip completely empty spans
            if span.text == "":
                continue

            if current is None:

                current = TextRun(
                    text=span.text,
                    font_size=span.font_size,
                    font_name=span.font,
                    color=span.color,
                    flags=span.flags,
                )

                continue

            same_style = (

                current.font_size == span.font_size

                and current.font_name == span.font

                and current.color == span.color

                and current.flags == span.flags
            )

            if same_style:

                current.text += span.text

            else:

                runs.append(current)

                current = TextRun(
                    text=span.text,
                    font_size=span.font_size,
                    font_name=span.font,
                    color=span.color,
                    flags=span.flags,
                )

        if current is not None:
            runs.append(current)

        return runs