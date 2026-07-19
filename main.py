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

print(
    "\nInitial profile models"
)

print(
    "Document profile:",
    document.profile
)

for page in document.pages:
    print(
        (
            f"Page {page.number}: "
            f"{page.profile.page_width:.2f} × "
            f"{page.profile.page_height:.2f}, "
            f"rotation={page.profile.rotation}, "
            f"type={page.profile.page_type.value}, "
            f"mode={page.profile.recommended_mode.value}"
        )
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

print(
    "\nPage profile analysis"
)

for page in document.pages:
    profile = page.profile

    print(
        f"\nPage {page.number}"
    )

    print(
        " Type:",
        profile.page_type.value,
    )

    print(
        " Recommended mode:",
        profile.recommended_mode.value,
    )

    print(
        " Size:",
        (
            round(
                profile.page_width,
                2,
            ),
            round(
                profile.page_height,
                2,
            ),
        ),
    )

    print(
        " Rotation:",
        profile.rotation,
    )

    print(
        " Text coverage:",
        round(
            profile.text_coverage,
            4,
        ),
    )

    print(
        " Image coverage:",
        round(
            profile.image_coverage,
            4,
        ),
    )

    print(
        " Vector coverage:",
        round(
            profile.vector_coverage,
            4,
        ),
    )

    print(
        " Table coverage:",
        round(
            profile.table_coverage,
            4,
        ),
    )

    print(
        " Chart coverage:",
        round(
            profile.chart_coverage,
            4,
        ),
    )

    print(
        " Columns:",
        profile.column_count,
    )

    print(
        " Tables:",
        profile.table_count,
    )

    print(
        " Charts:",
        profile.chart_count,
    )

    print(
        " OCR required:",
        profile.requires_ocr,
    )

    print(
        " Confidence:",
        {
            "editable": round(
                profile.editable_confidence,
                3,
            ),

            "fixed": round(
                profile.fixed_confidence,
                3,
            ),

            "hybrid": round(
                profile.hybrid_confidence,
                3,
            ),

            "ocr": round(
                profile.ocr_confidence,
                3,
            ),
        },
    )

    for reason in profile.reasons:
        print(
            "  Reason:",
            reason,
        )

    for warning in profile.warnings:
        print(
            "  Warning:",
            warning,
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