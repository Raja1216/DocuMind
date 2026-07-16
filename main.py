from src.analyzer.document_analyzer import (
    DocumentAnalyzer,
)
from src.exporter.fixed_layout_docx_exporter import (
    FixedLayoutDocxExporter,
)
from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader


reader = PDFReader()

pdf = reader.open(
    "samples/pdf/spdf4.pdf"
)

document = DocumentMapper.map(
    pdf
)
for page in document.pages:
    print(
        f"Page {page.number}: "
        f"{len(page.blocks)} text blocks, "
        f"{len(page.images)} images"
    )

    for table_index, table in enumerate(
        page.tables,
        start=1,
    ):
        print(
            f"  Table {table_index}: "
            f"{table.row_count} rows x "
            f"{table.column_count} columns"
        )

        print(
            "  Bounding box:",
            (
                table.left,
                table.top,
                table.right,
                table.bottom,
            ),
        )

        for cell in table.cells:
            print(
                f"    [{cell.row_index}, "
                f"{cell.column_index}] "
                f"{cell.text!r}"
            )

analyzer = DocumentAnalyzer()

analyzer.analyze(
    document
)

FixedLayoutDocxExporter.export(
    document=document,
    output_path="output/output.docx",
)

print(
    "Fixed-layout DOCX created successfully!"
)