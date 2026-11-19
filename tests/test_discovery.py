from epb_power.discovery import discover, select_sources


def test_product_wise_precedes_truncated_june(tmp_path, detailed_factory, product_factory):
    detailed_factory(tmp_path / "2025_07_2026_06.xlsx", "July-June 2025-26", {"74000000": 1}, 100)
    product_factory(tmp_path / "download.xlsx", {"85042100": 2, "90283000": 3}, 5)
    infos = discover(tmp_path)
    selected, issues = select_sources(infos)
    assert selected["2026-06"].report_format == "product_wise_country"
    detailed = next(info for info in infos if info.report_format == "detailed")
    assert detailed.selection_reason == "supplemental_truncated_not_selected"
    assert not any("multiple" in message for message in issues)


def test_missing_product_wise_june_is_critical(tmp_path, detailed_factory):
    detailed_factory(tmp_path / "june.xlsx", "July-June 2025-26", {"74000000": 1}, 1)
    _, issues = select_sources(discover(tmp_path))
    assert any("authoritative product-wise source missing" in message for message in issues)

