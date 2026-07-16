from src.analyzer.layout_analyzer import LayoutAnalyzer
from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader

reader = PDFReader()

pdf = reader.open("samples/pdf/spdf1.pdf")

document = DocumentMapper.map(pdf)

for page in document.pages:

    print(f"\n===== PAGE {page.number} =====")

    blocks = page.blocks

    for i in range(len(blocks) - 1):

        current = blocks[i]
        nxt = blocks[i + 1]

        gap = LayoutAnalyzer.vertical_gap(
            current,
            nxt,
        )

        current_text = (
            current.lines[0].spans[0].text
            if current.lines and current.lines[0].spans
            else ""
        )

        next_text = (
            nxt.lines[0].spans[0].text
            if nxt.lines and nxt.lines[0].spans
            else ""
        )

        print("--------------------------------")

        print(f"Current : {current_text}")

        print(f"Next    : {next_text}")

        print(f"Gap     : {gap}")