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
    for table_index, table in enumerate(
        page.tables,
        start=1,
    ):
        print(
            f"Page {page.number}, "
            f"Table {table_index}: "
            f"{table.row_count} rows x "
            f"{table.column_count} columns"
        )

        print(
            "BBox:",
            (
                table.left,
                table.top,
                table.right,
                table.bottom,
            ),
        )

        for cell in table.cells:
            print(
                (
                    cell.row_index,
                    cell.column_index,
                    cell.text,
                )
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