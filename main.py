from src.parser.pdf_reader import PDFReader
from src.extractor.metadata_extractor import MetadataExtractor

reader = PDFReader()

document = reader.open("samples/pdf/spdf4.pdf")
metadata = MetadataExtractor().extract(document)

print("\n========== PDF Metadata ==========\n")

for key, value in metadata.items():
    print(f"{key:15}: {value}")