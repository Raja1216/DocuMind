from dataclasses import dataclass, field

from src.models.metadata import PDFMetadata
from src.models.page import Page
from src.models.document_statistics import DocumentStatistics
from src.models.document_profile import (
    DocumentProfile,
)


@dataclass(slots=True)
class Document:
    """
    Complete document.
    """

    metadata: PDFMetadata

    pages: list[Page] = field(default_factory=list)
    statistics: DocumentStatistics = field(
        default_factory=DocumentStatistics
    )
    profile: DocumentProfile = field(
        default_factory=DocumentProfile
    )