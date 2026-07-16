from src.analyzer.reading_order_engine import ReadingOrderEngine
from src.models.text_block import TextBlock


def block(number, left, top):

    return TextBlock(
        page_number=1,
        left=left,
        top=top,
        right=100,
        bottom=100,
        block_number=number,
    )


blocks = [

    block(3, 10, 300),

    block(1, 10, 20),

    block(2, 10, 120),
]

ordered = ReadingOrderEngine.sort_blocks(blocks)

for b in ordered:
    print(b.block_number)