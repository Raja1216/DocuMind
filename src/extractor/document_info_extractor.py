class DocumentInfoExtractor:
    """
    Extract basic information from a PDF document.
    """

    def extract(self, document):
        return {
            "page_count": len(document),
            "is_pdf": document.is_pdf,
            "is_encrypted": document.is_encrypted,
            "needs_pass": document.needs_pass,
            "permissions": document.permissions,
            "metadata": document.metadata,
        }