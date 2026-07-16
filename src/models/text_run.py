from dataclasses import dataclass


@dataclass(slots=True)
class TextRun:

    text: str

    font_name: str

    font_size: float

    color: int

    bold: bool = False

    italic: bool = False