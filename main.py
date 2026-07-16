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
    "samples/pdf/spdf3.pdf"
)

document = DocumentMapper.map(
    pdf
)
for page in document.pages:
    for index, table in enumerate(
        page.tables,
        start=1,
    ):
        print(
            f"Page {page.number}, "
            f"Table {index}:",
            table.border_style.color,
            table.border_style.thickness,
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