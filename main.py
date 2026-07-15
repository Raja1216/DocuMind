from src.parser.pdf_reader import PDFReader
from src.extractor.metadata_extractor import MetadataExtractor
from src.extractor.document_info_extractor import DocumentInfoExtractor


reader = PDFReader()

document = reader.open("samples/pdf/spdf4.pdf")


print("=" * 50)
print("DOCUMENT INFORMATION")
print("=" * 50)

info = DocumentInfoExtractor().extract(document)

for key, value in info.items():
    print(f"{key:20}: {value}")
