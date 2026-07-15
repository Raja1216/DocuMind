# import fitz

# doc = fitz.open("samples/pdf/spdf4.pdf")

# print(type(doc))
# print()

# for item in dir(doc):
#     if not item.startswith("_"):
#         print(item)


from src.models.geometry.rectangle import Rectangle

rect = Rectangle(
    left=10,
    top=20,
    right=110,
    bottom=220,
)

print(rect)
print(rect.width)
print(rect.height)