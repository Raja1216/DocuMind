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
    "samples/pdf/spdf8.pdf"
)

document = DocumentMapper.map(
    pdf
)
for page in document.pages:
    print(
        f"Page {page.number}: "
        f"{len(page.vector_graphics)} "
        f"vector graphics"
    )

    for graphic in page.vector_graphics:
        print(
            " ",
            graphic.sequence_number,
            graphic.drawing_type,
            (
                graphic.left,
                graphic.top,
                graphic.right,
                graphic.bottom,
            ),
            "stroke:",
            graphic.stroke_color,
            graphic.stroke_width,
            "fill:",
            graphic.fill_color,
            "items:",
            len(graphic.items),
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