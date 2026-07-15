import pprint

from src.parser.pdf_reader import PDFReader
from src.extractor.metadata_extractor import MetadataExtractor
from src.extractor.document_info_extractor import DocumentInfoExtractor
from src.extractor.page_extractor import PageExtractor

from src.extractor.text_block_extractor import TextBlockExtractor

reader = PDFReader()

document = reader.open("samples/pdf/spdf1.pdf")


print("=" * 50)
print("DOCUMENT INFORMATION")
print("=" * 50)

info = DocumentInfoExtractor().extract(document)

for key, value in info.items():
    print(f"{key:20}: {value}")
    
pages = PageExtractor().extract(document)

print("\n" + "=" * 60)
print("PAGES")
print("=" * 60)

for page in pages:
    print()

    print(f"Page : {page.number}")
    print(f"Width : {page.width}")
    print(f"Height : {page.height}")
    print(f"Left : {page.left}")
    print(f"Top : {page.top}")
    print(f"Right : {page.right}")
    print(f"Bottom : {page.bottom}")
    print(f"Rotation : {page.rotation}")
    
page = document.load_page(0)

data = TextBlockExtractor().extract(page)

pp = pprint.PrettyPrinter(indent=2, width=120)

pp.pprint(data)