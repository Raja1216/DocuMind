from src.parser.pdf_reader import PDFReader

reader = PDFReader()

document = reader.open("samples/pdf/spdf4.pdf")

print("PDF opened successfully!")

print(document)