from src.analyzer.document_analyzer import (
    DocumentAnalyzer,
)
from src.exporter.fixed_layout_docx_exporter import (
    FixedLayoutDocxExporter,
)
from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader
from src.exporter.docx_exporter import (
    DocxExporter,
)


reader = PDFReader()

pdf = reader.open(
    "samples/pdf/spdf1.pdf"
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

for page in document.pages:

    print(
        f"\nPage {page.number} paragraphs:",
        len(page.paragraph_regions),
    )

    for region in page.paragraph_regions:

        preview = (
            region.text
            .replace(
                "\n",
                " | ",
            )
        )

        if region.list_type:
            print(
                "   List:",
                region.list_type,
                region.list_marker,
                (
                    region.list_marker_left,
                    region.content_left,
                ),
            )

        if len(preview) > 100:
            preview = (
                preview[:97]
                + "..."
            )

        print(
            f"  Paragraph {region.region_number}:",
            (
                round(region.left, 2),
                round(region.top, 2),
                round(region.right, 2),
                round(region.bottom, 2),
            ),
        )

        print(
            "   Blocks:",
            region.source_block_numbers,
        )

        print(
            "   Marker:",
            region.list_marker,
        )

        print(
            "   Text:",
            preview,
        )
FixedLayoutDocxExporter.export(
    document=document,
    output_path="output/output.docx",
)

DocxExporter.export(
    document=document,
    output_path="output/editable.docx",
)

print(
    "Fixed-layout DOCX created successfully!"
)

print(
    "Editable DOCX created:",
    "output/editable.docx",
)