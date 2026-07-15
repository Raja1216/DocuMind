import pprint

from src.extractor.text_block_extractor import TextBlockExtractor
from src.mapper.block_mapper import BlockMapper
from src.parser.pdf_reader import PDFReader

reader = PDFReader()

document = reader.open("samples/pdf/spdf1.pdf")

page = document.load_page(0)

data = TextBlockExtractor().extract(page)

for block in data["blocks"]:

    if block["type"] != 0:
        continue

    model = BlockMapper.map(
        block,
        page_number=1
    )

    pprint.pp(model)

    break