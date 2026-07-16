from __future__ import annotations

from docx import Document as WordDocument
from docx.dml.color import RGBColor as WordRGBColor
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from lxml import etree

from src.exporter.font_name_resolver import (
    FontNameResolver,
)


class FixedLayoutDocxExporter:
    """
    Export a PDF document model as a fixed-layout DOCX.

    Every visible PDF text span is placed inside an
    absolutely positioned Word text box.

    This mode prioritizes visual fidelity and original
    pagination over normal Word paragraph reflow.
    """

    VML_NAMESPACE = (
        "urn:schemas-microsoft-com:vml"
    )

    OFFICE_NAMESPACE = (
        "urn:schemas-microsoft-com:office:office"
    )

    WORD_2003_NAMESPACE = (
        "urn:schemas-microsoft-com:office:word"
    )

    WORD_NAMESPACE = (
        "http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main"
    )

    VML_NAMESPACE_MAP = {
        "v": VML_NAMESPACE,
        "o": OFFICE_NAMESPACE,
        "w10": WORD_2003_NAMESPACE,
        "w": WORD_NAMESPACE,
    }
    
    TEXTBOX_WIDTH_PADDING = 3.0
    TEXTBOX_HEIGHT_PADDING = 6.0

    TEXTBOX_TOP_ADJUSTMENT = 1.5
    LINE_HEIGHT_FACTOR = 1.25

    ANCHOR_FONT_SIZE = 1.0
    ANCHOR_LINE_SPACING = 1.0

    _shape_id = 1

    @staticmethod
    def export(
        document,
        output_path: str,
    ) -> None:
        word_document = WordDocument()

        FixedLayoutDocxExporter._shape_id = 1

        for page_index, page in enumerate(
            document.pages
        ):
            section = (
                FixedLayoutDocxExporter
                ._prepare_page_section(
                    word_document=word_document,
                    page_index=page_index,
                )
            )

            FixedLayoutDocxExporter._configure_section(
                section=section,
                page=page,
            )

            anchor_paragraph = (
                FixedLayoutDocxExporter
                ._create_anchor_paragraph(
                    word_document
                )
            )

            FixedLayoutDocxExporter._render_page(
                anchor_paragraph=anchor_paragraph,
                page=page,
            )

        word_document.save(
            output_path
        )

    @staticmethod
    def _prepare_page_section(
        word_document,
        page_index: int,
    ):
        """
        Use the original first section for page 1.

        Every later PDF page gets a new Word section
        beginning on a new page.
        """

        if page_index == 0:
            return word_document.sections[0]

        return word_document.add_section(
            WD_SECTION.NEW_PAGE
        )

    @staticmethod
    def _configure_section(
        section,
        page,
    ) -> None:
        """
        Match the PDF page dimensions.

        Fixed-layout positioning is relative to the physical
        page, so all Word margins are set to zero.
        """

        section.page_width = Pt(
            page.bbox.width
        )

        section.page_height = Pt(
            page.bbox.height
        )

        zero = Pt(0)

        section.left_margin = zero
        section.right_margin = zero
        section.top_margin = zero
        section.bottom_margin = zero

        section.header_distance = zero
        section.footer_distance = zero
        section.gutter = zero

    @staticmethod
    def _create_anchor_paragraph(
        word_document,
    ):
        """
        Create a minimal paragraph that owns all floating
        text boxes on the current Word page.
        """

        paragraph = word_document.add_paragraph()

        paragraph_format = paragraph.paragraph_format

        paragraph_format.space_before = Pt(0)
        paragraph_format.space_after = Pt(0)

        paragraph_format.line_spacing_rule = (
            WD_LINE_SPACING.EXACTLY
        )

        paragraph_format.line_spacing = Pt(
            FixedLayoutDocxExporter
            .ANCHOR_LINE_SPACING
        )

        anchor_run = paragraph.add_run("")

        anchor_run.font.size = Pt(
            FixedLayoutDocxExporter
            .ANCHOR_FONT_SIZE
        )

        return paragraph

    @staticmethod
    def _render_page(
        anchor_paragraph,
        page,
    ) -> None:
        """
        Render every visible span at its PDF coordinates.

        Page numbers are intentionally included because
        fixed-layout mode aims to reproduce all visible
        PDF content.
        """

        for block in page.blocks:
            for line in block.lines:
                for span in line.spans:

                    if not span.text.strip():
                        continue

                    FixedLayoutDocxExporter._add_span_textbox(
                        anchor_paragraph=anchor_paragraph,
                        span=span,
                    )

    @staticmethod
    def _add_span_textbox(
        anchor_paragraph,
        span,
    ) -> None:
        """
        Create one absolutely positioned Word text box for
        one formatted PDF span.
        """

        left = span.left

        top = max(
            span.top
            - FixedLayoutDocxExporter.TEXTBOX_TOP_ADJUSTMENT,
            0.0,
        )

        width = max(
            span.right
            - span.left
            + FixedLayoutDocxExporter.TEXTBOX_WIDTH_PADDING,
            1.0,
        )

        pdf_span_height = max(
            span.bottom - span.top,
            1.0,
        )

        word_line_height = max(
            span.font_size
            * FixedLayoutDocxExporter.LINE_HEIGHT_FACTOR,
            pdf_span_height,
        )

        height = (
            word_line_height
            + FixedLayoutDocxExporter.TEXTBOX_HEIGHT_PADDING
        )

        shape_id = (
            FixedLayoutDocxExporter
            ._next_shape_id()
        )

        shape = (
            FixedLayoutDocxExporter
            ._create_textbox_shape(
                shape_id=shape_id,
                left=left,
                top=top,
                width=width,
                height=height,
            )
        )

        textbox = FixedLayoutDocxExporter._create_vml_element(
            "textbox"
        )

        textbox.set(
            "inset",
            "0,0,0,0",
        )

        textbox_content = OxmlElement(
            "w:txbxContent"
        )

        text_paragraph_element = OxmlElement(
            "w:p"
        )

        textbox_content.append(
            text_paragraph_element
        )

        textbox.append(
            textbox_content
        )

        shape.append(
            textbox
        )

        pict = OxmlElement(
            "w:pict"
        )

        pict.append(
            shape
        )

        anchor_run = anchor_paragraph.add_run()

        anchor_run._r.append(
            pict
        )

        text_paragraph = Paragraph(
            text_paragraph_element,
            anchor_paragraph._parent,
        )

        FixedLayoutDocxExporter._configure_text_paragraph(
            text_paragraph=text_paragraph,
            span=span,
        )

        FixedLayoutDocxExporter._add_formatted_run(
            text_paragraph=text_paragraph,
            span=span,
        )

    @staticmethod
    def _create_textbox_shape(
        shape_id: int,
        left: float,
        top: float,
        width: float,
        height: float,
    ):
        """
        Create an absolutely positioned VML text-box shape.

        VML elements are created using explicit namespace URLs
        because python-docx does not register the `v`, `o`, and
        `w10` prefixes in OxmlElement.
        """

        shape = FixedLayoutDocxExporter._create_vml_element(
            "shape"
        )

        shape.set(
            "id",
            f"DocuMindTextBox{shape_id}",
        )

        shape.set(
            "type",
            "#_x0000_t202",
        )

        shape.set(
            "stroked",
            "f",
        )

        shape.set(
            "filled",
            "f",
        )

        shape.set(
            (
                f"{{{FixedLayoutDocxExporter.OFFICE_NAMESPACE}}}"
                "allowincell"
            ),
            "f",
        )

        style = (
            "position:absolute;"
            f"margin-left:{left:.3f}pt;"
            f"margin-top:{top:.3f}pt;"
            f"width:{width:.3f}pt;"
            f"height:{height:.3f}pt;"
            "z-index:251659264;"
            "mso-position-horizontal-relative:page;"
            "mso-position-vertical-relative:page;"
            "mso-wrap-style:none;"
            "mso-fit-shape-to-text:t;"
        )

        shape.set(
            "style",
            style,
        )

        wrap = (
            FixedLayoutDocxExporter
            ._create_word_2003_element(
                "wrap"
            )
        )

        wrap.set(
            "type",
            "none",
        )

        shape.append(
            wrap
        )

        return shape

    @staticmethod
    def _create_vml_element(
        local_name: str,
    ):
        """
        Create a VML element with all namespaces required by
        Microsoft Word's legacy text-box format.
        """

        return etree.Element(
            (
                f"{{{FixedLayoutDocxExporter.VML_NAMESPACE}}}"
                f"{local_name}"
            ),
            nsmap=FixedLayoutDocxExporter.VML_NAMESPACE_MAP,
        )

    @staticmethod
    def _create_word_2003_element(
        local_name: str,
    ):
        """
        Create an element from the legacy Microsoft Word 2003
        namespace, such as w10:wrap.
        """

        return etree.Element(
            (
                f"{{"
                f"{FixedLayoutDocxExporter.WORD_2003_NAMESPACE}"
                f"}}{local_name}"
            )
        )

    @staticmethod
    def _configure_text_paragraph(
        text_paragraph,
        span,
    ) -> None:
        """
        Remove Word paragraph spacing inside the text box.
        """

        paragraph_format = (
            text_paragraph.paragraph_format
        )

        paragraph_format.space_before = Pt(0)
        paragraph_format.space_after = Pt(0)

        paragraph_format.left_indent = Pt(0)
        paragraph_format.right_indent = Pt(0)
        paragraph_format.first_line_indent = Pt(0)

        paragraph_format.line_spacing_rule = (
            WD_LINE_SPACING.EXACTLY
        )

        paragraph_format.line_spacing = Pt(
            max(
                span.font_size
                * FixedLayoutDocxExporter.LINE_HEIGHT_FACTOR,
                span.bottom - span.top,
            )
        )

    @staticmethod
    def _add_formatted_run(
        text_paragraph,
        span,
    ) -> None:
        """
        Add editable text and preserve typography.
        """

        run = text_paragraph.add_run(
            span.text
        )

        font = run.font

        font.size = Pt(
            span.font_size
        )

        FixedLayoutDocxExporter._apply_font_name(
            run=run,
            pdf_font_name=span.font,
        )

        font.color.rgb = WordRGBColor(
            span.color.red,
            span.color.green,
            span.color.blue,
        )

        run.bold = (
            FixedLayoutDocxExporter
            ._is_bold(span.flags)
        )

        run.italic = (
            FixedLayoutDocxExporter
            ._is_italic(span.flags)
        )

    @staticmethod
    def _apply_font_name(
        run,
        pdf_font_name: str,
    ) -> None:
        """
        Resolve and apply the PDF font family to every
        Word font slot.
        """

        word_font_name = FontNameResolver.resolve(
            pdf_font_name
        )

        run.font.name = word_font_name

        run_properties = (
            run._element.get_or_add_rPr()
        )

        font_properties = (
            run_properties.get_or_add_rFonts()
        )

        font_properties.set(
            qn("w:ascii"),
            word_font_name,
        )

        font_properties.set(
            qn("w:hAnsi"),
            word_font_name,
        )

        font_properties.set(
            qn("w:eastAsia"),
            word_font_name,
        )

        font_properties.set(
            qn("w:cs"),
            word_font_name,
        )

    @staticmethod
    def _is_bold(flags: int) -> bool:
        """
        PyMuPDF flag bit 4 represents bold text.
        """

        return bool(
            flags & (1 << 4)
        )

    @staticmethod
    def _is_italic(flags: int) -> bool:
        """
        PyMuPDF flag bit 1 represents italic text.
        """

        return bool(
            flags & (1 << 1)
        )

    @staticmethod
    def _next_shape_id() -> int:
        """
        Return a unique ID for every positioned text box.
        """

        shape_id = (
            FixedLayoutDocxExporter._shape_id
        )

        FixedLayoutDocxExporter._shape_id += 1

        return shape_id