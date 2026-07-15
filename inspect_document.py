import fitz

doc = fitz.open("samples/pdf/spdf4.pdf")

print(type(doc))
print()

for item in dir(doc):
    if not item.startswith("_"):
        print(item)