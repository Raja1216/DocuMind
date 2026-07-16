from src.exporter.docx_exporter import DocxExporter
from src.mapper.document_mapper import DocumentMapper
from src.parser.pdf_reader import PDFReader
from src.analyzer.document_analyzer import DocumentAnalyzer

reader = PDFReader()

pdf = reader.open("samples/pdf/spdf1.pdf")

document = DocumentMapper.map(pdf)

DocumentAnalyzer.analyze(document)

DocxExporter.export(
    document,
    "output/output.docx",
)

print("DOCX created successfully!")