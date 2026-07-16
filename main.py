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
    "samples/pdf/spdf5.pdf"
)

document = DocumentMapper.map(
    pdf
)
for page in document.pages:
    for table in page.tables:
        for cell in table.cells:
            if cell.fill_color is not None:
                print(
                    f"Page {page.number}, "
                    f"Cell ({cell.row_index}, "
                    f"{cell.column_index}): "
                    f"{cell.fill_color}"
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