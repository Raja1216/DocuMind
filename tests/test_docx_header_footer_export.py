from __future__ import annotations

import unittest

from docx import Document as WordDocument

from src.exporter.docx_exporter import (
    DocxExporter,
)


class DocxHeaderFooterExportTests(
    unittest.TestCase
):

    def test_page_field_xml_is_created(
        self,
    ) -> None:
        word_document = (
            WordDocument()
        )

        paragraph = (
            word_document
            .sections[0]
            .footer
            .paragraphs[0]
        )

        DocxExporter._append_word_field(
            word_paragraph=paragraph,
            instruction="PAGE",
            placeholder="1",
        )

        xml = paragraph._p.xml

        self.assertIn(
            "PAGE",
            xml,
        )

        self.assertIn(
            'w:fldCharType="begin"',
            xml,
        )

        self.assertIn(
            'w:fldCharType="end"',
            xml,
        )


if __name__ == "__main__":
    unittest.main()