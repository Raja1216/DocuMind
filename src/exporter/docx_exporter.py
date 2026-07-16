from __future__ import annotations

from docx import Document as WordDocument


class DocxExporter:
    """
    Export a DocuMind Document into a DOCX file.
    """

    @staticmethod
    def export(document, output_path: str) -> None:

        doc = WordDocument()

        for page in document.pages:

            for block in page.blocks:

                paragraph = doc.add_paragraph()

                for line in block.lines:

                    for span in line.spans:

                        paragraph.add_run(span.text)

                # Keep line separation
                paragraph.add_run("\n")

            # Keep page separation
            doc.add_page_break()

        doc.save(output_path)