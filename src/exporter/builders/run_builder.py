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
                
                bold = bool(span.flags & (1 << 4))
                italic = bool(span.flags & (1 << 1))

                current = TextRun(
                    text=span.text,
                    font_size=span.font_size,
                    font_name=span.font,
                    color=span.color,
                    bold=bold,
                    italic=italic,
                )

                continue

            same_style = (

                current.font_size == span.font_size

                and current.font_name == span.font

                and current.color == span.color

                and current.bold == bold
                and current.italic == italic
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
                    bold=bold,
                    italic=italic,
                )

        if current is not None:
            runs.append(current)

        return runs