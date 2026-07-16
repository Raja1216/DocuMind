from src.exporter.docx_exporter import DocxExporter
from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader

reader = PDFReader()

pdf = reader.open("samples/pdf/spdf1.pdf")

document = DocumentMapper.map(pdf)

DocxExporter.export(
    document=document,
    output_path="output/output.docx",
)

print("DOCX created successfully!")