from pathlib import Path

from epb_power.calculations import aggregate_groups, build_hs8_monthly
from epb_power.models import CommodityRow, WorkbookInfo


def info(period: str, cents: int) -> WorkbookInfo:
    item = WorkbookInfo(Path("x"), f"{period}.xlsx", "hash", "time", "detailed", period, period, True)
    item.rows = [CommodityRow(period, "85042100", 8, "Transformer", "Transformer", cents, item.filename, 6, "detailed")]
    return item


SCOPE = [{"hs8": "85042100", "product_group": "Transformers", "include": "Y", "review_status": "approved", "description": "Transformer"}]


def test_fytd_difference_and_fy_reset():
    selected = {"2025-07": info("2025-07", 10_000), "2025-08": info("2025-08", 13_000), "2026-07": info("2026-07", 5_000)}
    rows, _ = build_hs8_monthly(selected, SCOPE)
    lookup = {row["month"]: row for row in rows}
    assert lookup["2025-07"]["monthly_cents"] == 10_000
    assert lookup["2025-08"]["monthly_cents"] == 3_000
    assert lookup["2026-07"]["monthly_cents"] == 5_000


def test_negative_revision_retained_and_flagged():
    selected = {"2025-07": info("2025-07", 10_000), "2025-08": info("2025-08", 9_900)}
    rows, issues = build_hs8_monthly(selected, SCOPE)
    august = next(row for row in rows if row["month"] == "2025-08")
    assert august["monthly_cents"] == -100
    assert august["qa_status"] == "negative_revision"
    assert any(item["issue_code"] == "negative_revision" for item in issues)


def test_mom_zero_base_is_na():
    selected = {"2025-07": info("2025-07", 0), "2025-08": info("2025-08", 100)}
    detail, _ = build_hs8_monthly(selected, SCOPE)
    monthly = aggregate_groups(detail, SCOPE)
    august = next(row for row in monthly if row["month"] == "2025-08")
    assert august["mom_pct"] is None
    assert august["mom_reason"] == "new_activity"


def test_missing_june_makes_june_and_july_mom_na():
    selected = {"2026-05": info("2026-05", 10_000), "2026-07": info("2026-07", 5_000)}
    detail, _ = build_hs8_monthly(selected, SCOPE)
    monthly = aggregate_groups(detail, SCOPE)
    june = next(row for row in monthly if row["month"] == "2026-06")
    july = next(row for row in monthly if row["month"] == "2026-07")
    assert june["monthly_usd"] is None
    assert july["mom_pct"] is None
    assert july["mom_reason"] == "missing_prior_month"

