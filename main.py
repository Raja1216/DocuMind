from src.parser.pdf_reader import PDFReader
from src.extractor.metadata_extractor import MetadataExtractor
from src.extractor.document_info_extractor import DocumentInfoExtractor
from src.extractor.page_extractor import PageExtractor

reader = PDFReader()

document = reader.open("samples/pdf/spdf4.pdf")


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
    print(page)