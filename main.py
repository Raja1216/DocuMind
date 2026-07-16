from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader

reader = PDFReader()

pdf = reader.open("samples/pdf/spdf1.pdf")

document = DocumentMapper.map(pdf)

print("=" * 60)
print("DOCUMENT SUMMARY")
print("=" * 60)

print(f"Pages : {len(document.pages)}")

for page in document.pages:

    print(
        f"Page {page.number}: {len(page.blocks)} text blocks"
    )