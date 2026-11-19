from __future__ import annotations

from collections import Counter

from .models import WorkbookInfo


def issue(severity: str, code: str, period: str, message: str, source: str = "") -> dict[str, str]:
    return {
        "severity": severity,
        "issue_code": code,
        "period": period,
        "source_file": source,
        "message": message,
    }


def validate_sources(
    infos: list[WorkbookInfo], selected: dict[str, WorkbookInfo], selection_messages: list[str]
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for message in selection_messages:
        severity = "critical" if "critical:" in message or "missing_source" in message else "warning"
        issues.append(issue(severity, "source_selection", "", message))
    for info in infos:
        for error in info.parse_errors:
            severity = "critical" if info.selected else "warning"
            issues.append(issue(severity, "parse_error", info.period or "", error, info.filename))
        if info.selected and not info.header_valid:
            issues.append(issue("critical", "invalid_header", info.period or "", "Selected source header invalid", info.filename))
        if info.reported_total_cents is not None:
            level = 8 if info.report_format == "product_wise_country" else 2
            available_total = sum(row.cents for row in info.rows if row.level == level)
            gap = available_total - info.reported_total_cents
            if abs(gap) > 100 and info.selected:
                issues.append(
                    issue(
                        "critical",
                        "selected_source_total_gap",
                        info.period or "",
                        f"Highest available commodity level differs from reported total by USD {gap / 100:.2f}",
                        info.filename,
                    )
                )
    june_product = next(
        (i for i in infos if i.period == "2026-06" and i.report_format == "product_wise_country"), None
    )
    june_detailed = next(
        (i for i in infos if i.period == "2026-06" and i.report_format == "detailed"), None
    )
    if june_product:
        if "85" not in june_product.chapters or "90" not in june_product.chapters:
            issues.append(issue("critical", "june_missing_chapters", "2026-06", "Product-wise June lacks Chapter 85 or 90", june_product.filename))
        hs8_sum = sum(row.cents for row in june_product.rows if row.level == 8)
        if june_product.reported_total_cents is not None:
            gap = hs8_sum - june_product.reported_total_cents
            if abs(gap) > 100:
                issues.append(issue("critical", "june_total_gap", "2026-06", f"HS8-total gap USD {gap / 100:.2f}", june_product.filename))
            elif gap:
                issues.append(issue("info", "june_total_rounding", "2026-06", f"Accepted HS8-total rounding gap USD {gap / 100:.2f}", june_product.filename))
    if june_product and june_detailed:
        common = set(june_product.hs8) & set(june_detailed.hs8)
        mismatches = [code for code in common if abs(june_product.hs8[code].cents - june_detailed.hs8[code].cents) > 1]
        if mismatches:
            issues.append(issue("critical", "june_overlap_mismatch", "2026-06", f"{len(mismatches)} of {len(common)} overlapping HS8 codes mismatch", june_product.filename))
        else:
            issues.append(issue("info", "june_overlap_match", "2026-06", f"All {len(common)} overlapping HS8 codes agree within USD 0.01", june_product.filename))
        if "85" not in june_detailed.chapters:
            issues.append(issue("info", "unused_june_truncated", "2026-06", f"Original June detailed source is truncated at {len(june_detailed.hs8)} HS8 rows and was not selected", june_detailed.filename))
    description_map: dict[str, set[str]] = {}
    for info in selected.values():
        for code, row in info.hs8.items():
            description_map.setdefault(code, set()).add(row.description)
    changed = sum(len(values) > 1 for values in description_map.values())
    if changed:
        issues.append(issue("warning", "description_changes", "all", f"{changed} HS8 codes have description variants across sources"))
    return issues


def qa_summary(issues: list[dict[str, str]]) -> dict[str, object]:
    counts = Counter(item["severity"] for item in issues)
    return {
        "status": "FAIL" if counts["critical"] else "PASS_WITH_WARNINGS" if counts["warning"] else "PASS",
        "counts": dict(counts),
        "critical_issue_codes": sorted({i["issue_code"] for i in issues if i["severity"] == "critical"}),
    }


def publication_blockers(
    issues: list[dict[str, str]], *, allow_incomplete: bool, allow_draft_scope: bool
) -> set[str]:
    """Return critical issue codes not explicitly permitted for provisional output."""
    critical = {item["issue_code"] for item in issues if item["severity"] == "critical"}
    blockers: set[str] = set()
    if "scope_not_approved" in critical and not allow_draft_scope:
        blockers.add("scope_not_approved")
    data_critical = critical - {"scope_not_approved"}
    if data_critical and not allow_incomplete:
        blockers.update(data_critical)
    return blockers


def scope_coverage_issues(
    selected: dict[str, WorkbookInfo], scope: list[dict[str, str]]
) -> list[dict[str, str]]:
    included_codes = {row["hs8"] for row in scope if row.get("include", "").upper() == "Y"}
    relevant_hs4 = {code[:4] for code in included_codes}
    relevant_hs6 = {code[:6] for code in included_codes}
    issues: list[dict[str, str]] = []
    for month, info in selected.items():
        if info.report_format != "detailed":
            continue
        row_map = {row.code: row for row in info.rows}
        for parent in sorted(relevant_hs4 | relevant_hs6):
            parent_row = row_map.get(parent)
            if parent_row is None:
                continue
            children = [row for row in info.rows if row.level == 8 and row.code.startswith(parent)]
            gap = parent_row.cents - sum(row.cents for row in children)
            if abs(gap) > 1:
                issues.append(
                    issue(
                        "warning",
                        "scope_heading_hs8_gap",
                        month,
                        f"Relevant heading {parent} subtotal minus available HS8 children = USD {gap / 100:.2f}",
                        info.filename,
                    )
                )
    return issues

