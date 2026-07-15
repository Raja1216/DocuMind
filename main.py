import pprint

from src.extractor.text_block_extractor import TextBlockExtractor
from src.mapper.line_mapper import LineMapper
from src.parser.pdf_reader import PDFReader

reader = PDFReader()

document = reader.open("samples/pdf/spdf1.pdf")

page = document.load_page(0)

data = TextBlockExtractor().extract(page)

for block in data["blocks"]:

    if block["type"] != 0:
        continue

    for line in block["lines"]:

        model = LineMapper.map(line)

        pprint.pp(model)

        break

    break