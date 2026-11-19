from epb_power.parser import inspect_workbook, parse_period, to_cents


def test_period_parsing_all_fy_shapes():
    assert parse_period("Period: July 2025-26") == "2025-07"
    assert parse_period("Period: July-December 2025-26") == "2025-12"
    assert parse_period("Period: July-January 2025-26") == "2026-01"
    assert parse_period("Period: July-June 2025-26") == "2026-06"


def test_decimal_currency_to_cents():
    assert to_cents("1,234.567") == 123457
    assert to_cents(-0.01) == -1


def test_detailed_hierarchy_and_total(tmp_path, detailed_factory):
    path = detailed_factory(
        tmp_path / "source.xlsx",
        "July-August 2025-26",
        {"01": 10, "0101": 10, "010101": 10, "01010100": 10.25},
        10.25,
    )
    info = inspect_workbook(path)
    assert info.period == "2025-08"
    assert info.counts == {2: 1, 4: 1, 6: 1, 8: 1}
    assert info.hs8["01010100"].cents == 1025
    assert info.reported_total_cents == 1025


def test_duplicate_detection(tmp_path, detailed_factory):
    path = detailed_factory(tmp_path / "dup.xlsx", "July 2025-26", {"85042100": 1})
    from openpyxl import load_workbook

    wb = load_workbook(path)
    ws = wb["Worksheet 1"]
    ws["A7"], ws["B7"] = "85042100: duplicate", 2
    wb.save(path)
    info = inspect_workbook(path)
    assert any("duplicate_code" in error for error in info.parse_errors)


def test_product_subtotals_not_country_rows(tmp_path, product_factory):
    info = inspect_workbook(product_factory(tmp_path / "opaque.xlsx", {"85042100": 12.34}, 12.34))
    assert info.report_format == "product_wise_country"
    assert info.period == "2026-06"
    assert info.counts[8] == 1
    assert info.country_rows == 1
    assert info.hs8["85042100"].cents == 1234

