from __future__ import annotations

import html
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook

from .models import CommodityRow, WorkbookInfo
from .provenance import sha256_file

CODE_RE = re.compile(r"^\s*(\d{2}|\d{4}|\d{6}|\d{8})\s*:\s*(.*)$")
HS8_RE = re.compile(r"^\s*(\d{8})\s*:\s*(.*)$")
PERIOD_RE = re.compile(
    r"Period\s*:\s*(?:July\s*-\s*)?([A-Za-z]+)(?:\s+|\s*-\s*)(20\d{2})(?:\s*-\s*(\d{2}))?",
    re.I,
)
MONTHS = {
    name.lower(): number
    for number, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        1,
    )
}


class ParseError(ValueError):
    pass


def to_cents(value: object) -> int:
    if value is None or value == "":
        raise ParseError("missing currency value")
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ParseError(f"invalid currency value {value!r}") from exc
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_period(text: object) -> str | None:
    value = str(text or "").replace("–", "-").replace("—", "-")
    match = PERIOD_RE.search(value)
    if not match:
        return None
    end_month_name, start_year_text, _ = match.groups()
    month = MONTHS.get(end_month_name.lower())
    if month is None:
        return None
    start_year = int(start_year_text)
    year = start_year if month >= 7 else start_year + 1
    return f"{year:04d}-{month:02d}"


def _base_info(path: Path) -> WorkbookInfo:
    return WorkbookInfo(
        path=path,
        filename=path.name,
        sha256=sha256_file(path),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
    )


def inspect_workbook(path: Path) -> WorkbookInfo:
    info = _base_info(path)
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises several format/zip exceptions
        info.parse_errors.append(f"cannot_open: {exc}")
        return info
    try:
        sheets = set(workbook.sheetnames)
        if {"2 Digit", "4 Digit", "6 Digit", "8 Digit"}.issubset(sheets):
            _parse_product_wise(workbook, info)
        elif "Worksheet 1" in sheets:
            _parse_detailed(workbook, info)
        else:
            info.parse_errors.append(f"unrecognized_sheets: {workbook.sheetnames}")
    finally:
        workbook.close()
    info.counts = {level: sum(row.level == level for row in info.rows) for level in (2, 4, 6, 8)}
    info.chapters = {row.code[:2] for row in info.rows if row.level == 8}
    return info


def _parse_detailed(workbook: object, info: WorkbookInfo) -> None:
    sheet = workbook["Worksheet 1"]
    info.report_format = "detailed"
    info.period_text = str(sheet["A3"].value or "")
    info.period = parse_period(info.period_text)
    info.header_valid = (
        str(sheet["A1"].value or "").strip() == "Export Promotion Bureau"
        and "Commodity wise Detailed Data" in str(sheet["A2"].value or "")
        and str(sheet["A5"].value or "").strip() == "HS Code"
        and str(sheet["B5"].value or "").strip() == "USD"
    )
    if not info.header_valid:
        info.parse_errors.append("invalid_detailed_header")
    seen: set[str] = set()
    for row_number, (a_value, b_value) in enumerate(
        sheet.iter_rows(min_row=6, max_col=2, values_only=True), start=6
    ):
        text = str(a_value or "")
        match = CODE_RE.match(text)
        if match:
            code, raw_description = match.groups()
            try:
                cents = to_cents(b_value)
            except ParseError as exc:
                info.parse_errors.append(f"row_{row_number}_{code}: {exc}")
                continue
            if code in seen:
                info.parse_errors.append(f"duplicate_code: {code} row {row_number}")
            seen.add(code)
            info.rows.append(
                CommodityRow(
                    info.period or "unknown",
                    code,
                    len(code),
                    html.unescape(raw_description).strip(),
                    raw_description,
                    cents,
                    info.filename,
                    row_number,
                    info.report_format,
                )
            )
        elif text.strip().lower() == "total":
            try:
                info.reported_total_cents = to_cents(b_value)
            except ParseError as exc:
                info.parse_errors.append(f"total: {exc}")


def _parse_product_wise(workbook: object, info: WorkbookInfo) -> None:
    sheet = workbook["8 Digit"]
    info.report_format = "product_wise_country"
    info.period_text = str(sheet["A3"].value or "")
    info.period = parse_period(info.period_text)
    info.header_valid = (
        str(sheet["A1"].value or "").strip() == "Export Promotion Bureau"
        and "Commodity-wise Data of Countries" in str(sheet["A2"].value or "")
        and str(sheet["A5"].value or "").strip() == "HS Code"
        and str(sheet["B5"].value or "").strip() == "Country"
        and str(sheet["C5"].value or "").strip() == "USD"
    )
    if not info.header_valid:
        info.parse_errors.append("invalid_product_wise_header")
    seen: set[str] = set()
    for row_number, (a_value, b_value, c_value) in enumerate(
        sheet.iter_rows(min_row=6, max_col=3, values_only=True), start=6
    ):
        a_text = str(a_value or "")
        match = HS8_RE.match(a_text)
        country_blank = b_value is None or str(b_value).strip() == ""
        if match and country_blank:
            code, raw_description = match.groups()
            try:
                cents = to_cents(c_value)
            except ParseError as exc:
                info.parse_errors.append(f"row_{row_number}_{code}: {exc}")
                continue
            if code in seen:
                info.parse_errors.append(f"duplicate_code: {code} row {row_number}")
            seen.add(code)
            info.rows.append(
                CommodityRow(
                    info.period or "unknown",
                    code,
                    8,
                    html.unescape(raw_description).strip(),
                    raw_description,
                    cents,
                    info.filename,
                    row_number,
                    info.report_format,
                )
            )
        elif (a_value is None or not str(a_value).strip()) and b_value not in (None, ""):
            info.country_rows += 1
        elif str(a_value or "").strip().lower() == "total":
            try:
                info.reported_total_cents = to_cents(c_value)
            except ParseError as exc:
                info.parse_errors.append(f"total: {exc}")

