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

    print(
        f"\nPage {page.number}"
    )

    print(
        " Renderable vectors:",
        sum(
            g.should_render
            for g in page.vector_graphics
        )
    )

    print(
        " Regions:",
        len(page.vector_regions)
    )

    for region in page.vector_regions:

        print(
            f"  Region {region.region_number}:",
            len(region.graphics),
            "graphics",
            (
                region.left,
                region.top,
                region.right,
                region.bottom,
            )
        )
        print(
            "   Image:",
            region.image_path,
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