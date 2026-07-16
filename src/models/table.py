from __future__ import annotations

from dataclasses import dataclass, field

from src.models.base_element import BaseElement
from src.models.table_cell import TableCell
from src.models.table_border_style import TableBorderStyle


@dataclass(slots=True)
class Table(BaseElement):
    """
    Represents one logical table detected on a PDF page.
    """

    row_count: int
    column_count: int

    cells: list[TableCell] = field(
        default_factory=list
    )

    border_style: TableBorderStyle = field(
        default_factory=TableBorderStyle
    )
    
    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def get_cell(
        self,
        row_index: int,
        column_index: int,
    ) -> TableCell | None:
        """
        Return one cell by its row and column indexes.
        """

        for cell in self.cells:
            if (
                cell.row_index == row_index
                and cell.column_index == column_index
            ):
                return cell

        return None