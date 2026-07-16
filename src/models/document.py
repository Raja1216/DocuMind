from dataclasses import dataclass, field

from src.models.metadata import PDFMetadata
from src.models.page import Page


@dataclass(slots=True)
class Document:
    """
    Complete document.
    """

    metadata: PDFMetadata

    pages: list[Page] = field(default_factory=list)