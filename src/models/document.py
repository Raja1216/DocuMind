from dataclasses import dataclass, field

from src.models.metadata import PDFMetadata
from src.models.page import Page
from src.models.text_block import TextBlock


@dataclass(slots=True)
class Document:
    metadata: PDFMetadata

    pages: list[Page] = field(default_factory=list)

    blocks: list[TextBlock] = field(default_factory=list)