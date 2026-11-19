from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import EXPECTED_MONTHS, WorkbookInfo
from .parser import inspect_workbook


def discover(data_dir: Path) -> list[WorkbookInfo]:
    return [inspect_workbook(path) for path in sorted(data_dir.glob("*.xlsx"))]


def select_sources(infos: list[WorkbookInfo]) -> tuple[dict[str, WorkbookInfo], list[str]]:
    by_period: dict[str, list[WorkbookInfo]] = defaultdict(list)
    issues: list[str] = []
    for info in infos:
        if info.period and info.header_valid:
            by_period[info.period].append(info)
        else:
            info.selection_reason = "unrecognized_or_invalid"
            issues.append(f"{info.filename}: unrecognized/invalid workbook or period")

    selected: dict[str, WorkbookInfo] = {}
    for period in EXPECTED_MONTHS:
        candidates = by_period.get(period, [])
        if not candidates:
            issues.append(f"missing_source: {period}")
            continue
        if period == "2026-06":
            preferred = [c for c in candidates if c.report_format == "product_wise_country"]
            if len(preferred) == 1:
                choice = preferred[0]
                for item in candidates:
                    if item is not choice:
                        item.selection_reason = "supplemental_truncated_not_selected"
            elif not preferred:
                issues.append("critical: June 2026 authoritative product-wise source missing")
                continue
            else:
                issues.append("critical: multiple product-wise June 2026 sources")
                continue
        else:
            preferred = [c for c in candidates if c.report_format == "detailed"]
            if len(preferred) != 1:
                issues.append(f"critical: {period} has {len(preferred)} detailed candidates")
                continue
            choice = preferred[0]
            for item in candidates:
                if item is not choice:
                    item.selection_reason = "unexpected_competing_source"
        choice.selected = True
        choice.selection_reason = "authoritative_selected"
        selected[period] = choice
    return selected, issues

