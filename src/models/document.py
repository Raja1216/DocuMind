from dataclasses import dataclass, field
from typing import Any

from src.models.metadata import PDFMetadata
from src.models.page import Page
from src.models.document_statistics import DocumentStatistics
from src.models.document_profile import (
    DocumentProfile,
)
from src.models.alignment_validation import (
    AlignmentValidationReport,
)


@dataclass(slots=True)
class Document:
    """
    Complete document.
    """

    metadata: PDFMetadata

    # Runtime-only reference that keeps the source PDF alive for
    # region fallback rendering. It is not part of the semantic
    # document model and is excluded from repr output.
    source_pdf_document: Any | None = field(
        default=None,
        repr=False,
    )

    pages: list[Page] = field(default_factory=list)
    statistics: DocumentStatistics = field(
        default_factory=DocumentStatistics
    )
    profile: DocumentProfile = field(
        default_factory=DocumentProfile
    )
    alignment_validation_report: (
        AlignmentValidationReport
    ) = field(
        default_factory=AlignmentValidationReport
    )