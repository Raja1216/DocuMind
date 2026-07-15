import pprint

from src.parser.pdf_reader import PDFReader
from src.extractor.text_block_extractor import TextBlockExtractor
from src.mapper.span_mapper import SpanMapper

reader = PDFReader()

document = reader.open("samples/pdf/spdf1.pdf")

page = document.load_page(0)

data = TextBlockExtractor().extract(page)

mapper = SpanMapper()

for block in data["blocks"]:

    if block["type"] != 0:
        continue

    for line in block["lines"]:

        for span in line["spans"]:

            model = mapper.map(span)

            pprint.pp(model)

            break

        break

    break