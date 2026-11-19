from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import EXPECTED_MONTHS, WorkbookInfo


def fiscal_year(month: str) -> str:
    year, number = (int(value) for value in month.split("-"))
    return f"{year}-{str(year + 1)[-2:]}" if number >= 7 else f"{year - 1}-{str(year)[-2:]}"


def build_hs8_monthly(
    selected: dict[str, WorkbookInfo], scope: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    included = {item["hs8"]: item for item in scope if item.get("include", "").upper() == "Y"}
    records: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    previous: dict[tuple[str, str], int | None] = {}
    observed_positive: set[tuple[str, str]] = set()
    for month in EXPECTED_MONTHS:
        source = selected.get(month)
        fy = fiscal_year(month)
        month_number = int(month[-2:])
        for code, scope_row in included.items():
            row = source.hs8.get(code) if source else None
            key = (fy, code)
            cumulative: int | None
            status = "valid"
            reason = ""
            source_file = source.filename if source else ""
            source_row: int | None = row.source_row if row else None
            if source is None:
                cumulative = None
                status, reason = "missing_source", "No authoritative source for month"
            elif row is not None:
                cumulative = row.cents
                if cumulative > 0:
                    observed_positive.add(key)
            elif key not in observed_positive:
                cumulative = 0
                status, reason = "no_export_evidence", "Code absent before its first positive cumulative observation"
            else:
                cumulative = None
                status, reason = "incomplete_source", "Previously positive included code disappeared from cumulative source"
                issues.append(
                    {
                        "severity": "critical",
                        "issue_code": "included_code_disappeared",
                        "period": month,
                        "source_file": source_file,
                        "message": f"{code} disappeared after a positive cumulative observation",
                    }
                )
            monthly: int | None = None
            prior_value: int | None = None
            if cumulative is not None:
                if month_number == 7:
                    monthly = cumulative
                else:
                    prior_value = previous.get(key, 0)
                    if prior_value is None:
                        status = "incomplete_source"
                        reason = "Immediately preceding cumulative value is missing"
                    else:
                        monthly = cumulative - prior_value
                if monthly is not None and monthly < 0:
                    status = "negative_revision"
                    reason = "Negative first difference; may reflect source revision/reclassification, not negative shipments"
                    issues.append(
                        {
                            "severity": "warning",
                            "issue_code": "negative_revision",
                            "period": month,
                            "source_file": source_file,
                            "message": f"{code} monthly net cumulative delta is USD {monthly / 100:.2f}",
                        }
                    )
            previous[key] = cumulative
            records.append(
                {
                    "month": month,
                    "fiscal_year": fy,
                    "hs8": code,
                    "product_group": scope_row["product_group"],
                    "description": scope_row.get("description", row.description if row else ""),
                    "cumulative_cents": cumulative,
                    "monthly_cents": monthly,
                    "cumulative_usd": None if cumulative is None else cumulative / 100,
                    "monthly_usd": None if monthly is None else monthly / 100,
                    "qa_status": status,
                    "issue_reason": reason,
                    "source_file": source_file,
                    "source_row": source_row,
                    "calculation": "July FYTD" if month_number == 7 else "current FYTD minus prior-month FYTD",
                }
            )
    return records, issues


def aggregate_groups(detail: list[dict[str, Any]], scope: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups = sorted({item["product_group"] for item in scope if item.get("include", "").upper() == "Y"})
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in detail:
        by_key[(row["month"], row["product_group"])].append(row)
    monthly_rows: list[dict[str, Any]] = []
    for month in EXPECTED_MONTHS:
        for group in groups:
            rows = by_key[(month, group)]
            values = [row["monthly_cents"] for row in rows]
            valid = bool(rows) and all(value is not None for value in values)
            cents = sum(values) if valid else None
            statuses = sorted({row["qa_status"] for row in rows if row["qa_status"] != "valid"})
            monthly_rows.append(
                {
                    "month": month,
                    "product_group": group,
                    "monthly_cents": cents,
                    "monthly_usd": None if cents is None else cents / 100,
                    "monthly_usd_million": None if cents is None else cents / 100_000_000,
                    "qa_status": "valid" if not statuses else ";".join(statuses),
                    "issue_reason": "" if not statuses else "One or more HS8 records require qualification",
                }
            )
    totals: dict[str, int | None] = {}
    for month in EXPECTED_MONTHS:
        month_values = [r["monthly_cents"] for r in monthly_rows if r["month"] == month]
        totals[month] = sum(month_values) if month_values and all(v is not None for v in month_values) else None
    previous: dict[str, int | None] = {}
    for row in monthly_rows:
        group, cents = row["product_group"], row["monthly_cents"]
        prior = previous.get(group)
        if row["month"] == EXPECTED_MONTHS[0]:
            change = pct = None
            reason = "missing_prior_month"
        elif cents is None or prior is None:
            change = pct = None
            reason = "missing_prior_month" if prior is None else "missing_current_month"
        else:
            change = cents - prior
            if prior > 0:
                pct = change / prior * 100
                reason = ""
            else:
                pct = None
                reason = "new_activity" if prior == 0 and cents > 0 else "zero_base"
        total = totals[row["month"]]
        row["mom_change_cents"] = change
        row["mom_change_usd"] = None if change is None else change / 100
        row["mom_pct"] = pct
        row["mom_reason"] = reason
        row["share_pct"] = cents / total * 100 if cents is not None and total not in (None, 0) else None
        previous[group] = cents
    return monthly_rows

