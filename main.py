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
    print(
        f"Page {page.number}: "
        f"{len(page.blocks)} text blocks, "
        f"{len(page.images)} images"
    )

    for image in page.images:
        print(
            "  Image:",
            image.extension,
            image.pixel_width,
            "x",
            image.pixel_height,
            "at",
            (
                image.left,
                image.top,
                image.right,
                image.bottom,
            ),
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