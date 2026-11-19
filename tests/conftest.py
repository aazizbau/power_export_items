from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook


@pytest.fixture
def detailed_factory():
    def create(path: Path, period: str, values: dict[str, float], total: float | None = None) -> Path:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Worksheet 1"
        sheet["A1"] = "Export Promotion Bureau"
        sheet["A2"] = "Report: Commodity wise Detailed Data"
        sheet["A3"] = f"Period: {period}"
        sheet["A5"], sheet["B5"] = "HS Code", "USD"
        row = 6
        for code, value in values.items():
            sheet.cell(row, 1, f"{code}: Description {code}")
            sheet.cell(row, 2, value)
            row += 1
        if total is not None:
            sheet.cell(row, 1, "Total")
            sheet.cell(row, 2, total)
        workbook.save(path)
        return path

    return create


@pytest.fixture
def product_factory():
    def create(path: Path, values: dict[str, float], total: float) -> Path:
        workbook = Workbook()
        workbook.remove(workbook.active)
        for name in ("2 Digit", "4 Digit", "6 Digit", "8 Digit"):
            sheet = workbook.create_sheet(name)
            sheet["A1"] = "Export Promotion Bureau"
            sheet["A2"] = "Report: Commodity-wise Data of Countries"
            sheet["A3"] = "Period: July-June 2025-26"
            if name == "8 Digit":
                sheet["A5"], sheet["B5"], sheet["C5"] = "HS Code", "Country", "USD"
                row = 6
                for code, value in values.items():
                    sheet.cell(row, 1, f"{code}: Product {code}")
                    sheet.cell(row, 3, value)
                    sheet.cell(row + 1, 2, "BD: Bangladesh")
                    sheet.cell(row + 1, 3, value)
                    row += 2
                sheet.cell(row, 1, "Total")
                sheet.cell(row, 3, total)
        workbook.save(path)
        return path

    return create

