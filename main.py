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
    # "samples/BirlaPDF/Class-4-Print31 1.pdf"
)

document = DocumentMapper.map(
    pdf
)
for page in document.pages:

    renderable_graphics = [
        graphic
        for graphic in page.vector_graphics
        if graphic.should_render
    ]

    print(
        f"Page {page.number}: "
        f"{len(page.vector_graphics)} extracted, "
        f"{len(renderable_graphics)} renderable"
    )

    category_counts = {}

    for graphic in page.vector_graphics:
        category_counts[
            graphic.category
        ] = (
            category_counts.get(
                graphic.category,
                0,
            )
            + 1
        )

    print(
        "  Categories:",
        category_counts,
    )

    for graphic in renderable_graphics:
        print(
            " ",
            graphic.sequence_number,
            graphic.category,
            graphic.drawing_type,
            (
                graphic.left,
                graphic.top,
                graphic.right,
                graphic.bottom,
            ),
            "fill:",
            graphic.fill_color,
            "stroke:",
            graphic.stroke_color,
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