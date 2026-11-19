from pathlib import Path

import pytest

from epb_power.calculations import build_hs8_monthly
from epb_power.discovery import discover, select_sources
from epb_power.scope import read_scope


@pytest.mark.integration
def test_local_source_inventory_and_authoritative_june():
    data_dir = Path("data")
    if not list(data_dir.glob("*.xlsx")):
        pytest.skip("local EPB workbooks unavailable")
    infos = discover(data_dir)
    selected, messages = select_sources(infos)
    assert len(infos) == 17
    assert len(selected) == 16
    assert not [message for message in messages if "critical:" in message or "missing_source" in message]
    june = selected["2026-06"]
    assert june.report_format == "product_wise_country"
    assert len(june.hs8) == 2399
    assert {"85", "90"}.issubset(june.chapters)
    truncated = next(info for info in infos if info.period == "2026-06" and info.report_format == "detailed")
    assert len(truncated.hs8) == 1110
    assert all(abs(june.hs8[code].cents - truncated.hs8[code].cents) <= 1 for code in truncated.hs8)
    expected = {
        "2025_07.xlsx": "2025-07",
        "2025_07_08.xlsx": "2025-08",
        "2025_07_09.xlsx": "2025-09",
        "2025_07_10.xlsx": "2025-10",
        "2025_07_11.xlsx": "2025-11",
        "2025_07_12.xlsx": "2025-12",
        "2025_07_2026_01.xlsx": "2026-01",
        "2025_07_2026_02.xlsx": "2026-02",
        "2025_07_2026_03.xlsx": "2026-03",
        "2025_07_2026_04.xlsx": "2026-04",
        "2025_07_2026_05.xlsx": "2026-05",
        "2025_07_2026_06.xlsx": "2026-06",
        "2026_07.xlsx": "2026-07",
        "2026_07_08.xlsx": "2026-08",
        "2026_07_09.xlsx": "2026-09",
        "2026_07_10.xlsx": "2026-10",
    }
    actual = {info.filename: info.period for info in infos if info.filename in expected}
    assert actual == expected


@pytest.mark.integration
def test_local_panel_has_16_months():
    if not Path("config/hs_scope.csv").exists():
        pytest.skip("scope unavailable")
    infos = discover(Path("data"))
    selected, _ = select_sources(infos)
    detail, _ = build_hs8_monthly(selected, read_scope(Path("config/hs_scope.csv")))
    assert len({row["month"] for row in detail}) == 16

