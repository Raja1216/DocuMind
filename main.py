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

    policy = page.conversion_policy

    if policy is None:
        print(
            " Conversion policy: unavailable"
        )

    else:
        print(
            " Conversion policy"
        )

        print(
            "  Mode:",
            policy.mode.value,
        )

        print(
            "  Text paragraphs:",
            policy.export_text_as_paragraphs,
        )

        print(
            "  Word lists:",
            policy.export_lists_as_word_lists,
        )

        print(
            "  Word tables:",
            policy.export_tables_as_word_tables,
        )

        print(
            "  Form controls:",
            policy.export_forms_as_controls,
        )

        print(
            "  Images:",
            policy.export_images_as_images,
        )

        print(
            "  Vector images:",
            policy.export_vectors_as_images,
        )

        print(
            "  Chart images:",
            policy.export_charts_as_images,
        )

        print(
            "  Run OCR:",
            policy.run_ocr,
        )

        print(
            "  Include OCR text:",
            policy.include_ocr_text,
        )

        print(
            "  Full-page image:",
            policy.use_full_page_image,
        )

        print(
            "  Region fallback:",
            policy.allow_region_image_fallback,
        )

        print(
            "  Confidence:",
            round(
                policy.confidence,
                3,
            ),
        )

        print(
            "  Reason:",
            policy.reason,
        )

        for warning in policy.warnings:
            print(
                "   Warning:",
                warning,
            )

for page in document.pages:
    profile = page.profile

    print(
        f"\nPage {page.number}"
    )
    
    print(
        " Layout regions:",
        len(
            page.layout_regions
        ),
    )
    
    for region in page.layout_regions:
        print(
            (
                f"  Region {region.region_id}: "
                f"{region.region_type.value}, "
                f"bbox=("
                f"{region.left:.2f}, "
                f"{region.top:.2f}, "
                f"{region.right:.2f}, "
                f"{region.bottom:.2f}), "
                f"paragraphs="
                f"{region.paragraph_region_numbers}, "
                f"confidence="
                f"{region.confidence:.3f}"
            )
        )
    
    print(
        " Column regions:",
        len(
            page.column_regions
        ),
    )
    
    for column in page.column_regions:
        print(
            (
                f"  Column {column.column_index + 1}: "
                f"bbox=("
                f"{column.left:.2f}, "
                f"{column.top:.2f}, "
                f"{column.right:.2f}, "
                f"{column.bottom:.2f}), "
                f"paragraphs="
                f"{column.paragraph_region_numbers}, "
                f"confidence="
                f"{column.confidence:.3f}"
            )
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
        
document_profile = document.profile

print(
    "\nDocument profile analysis"
)

print(
    " Page count:",
    document_profile.page_count,
)

print(
    " Dominant page type:",
    document_profile.dominant_page_type.value,
)

print(
    " Recommended mode:",
    document_profile.recommended_mode.value,
)

print(
    " Digital pages:",
    document_profile.digital_page_count,
)

print(
    " Scanned pages:",
    document_profile.scanned_page_count,
)

print(
    " Mixed pages:",
    document_profile.mixed_page_count,
)

print(
    " Page type counts:",
    document_profile.page_type_counts,
)

print(
    " Mode counts:",
    document_profile.mode_counts,
)

print(
    " Contains tables:",
    document_profile.contains_tables,
)

print(
    " Contains charts:",
    document_profile.contains_charts,
)

print(
    " Contains forms:",
    document_profile.contains_forms,
)

print(
    " Contains scanned pages:",
    document_profile.contains_scanned_pages,
)

print(
    " Multiple page sizes:",
    document_profile.contains_multiple_page_sizes,
)

print(
    " Multiple orientations:",
    document_profile.contains_multiple_orientations,
)

print(
    " Requires OCR:",
    document_profile.requires_ocr,
)

print(
    " Requires hybrid conversion:",
    document_profile.requires_hybrid_conversion,
)

print(
    " Confidence:",
    {
        "editable": round(
            document_profile.editable_confidence,
            3,
        ),
        "fixed": round(
            document_profile.fixed_confidence,
            3,
        ),
        "hybrid": round(
            document_profile.hybrid_confidence,
            3,
        ),
        "ocr": round(
            document_profile.ocr_confidence,
            3,
        ),
    },
)

for reason in document_profile.reasons:
    print(
        "  Reason:",
        reason,
    )

for warning in document_profile.warnings:
    print(
        "  Warning:",
        warning,
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