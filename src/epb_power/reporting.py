from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from . import __version__
from .charts import write_png_charts
from .models import EXPECTED_MONTHS, WorkbookInfo

PROVISIONAL_WARNING = (
    "PROVISIONAL — NOT FOR OFFICIAL PUBLICATION: unresolved QA blockers and/or draft HS scope remain."
)


def source_manifest(infos: list[WorkbookInfo]) -> list[dict[str, Any]]:
    records = []
    for info in infos:
        hs8_sum = sum(row.cents for row in info.rows if row.level == 8)
        top_level = 8 if info.report_format == "product_wise_country" else 2
        top_sum = sum(row.cents for row in info.rows if row.level == top_level)
        total_gap = None if info.reported_total_cents is None else top_sum - info.reported_total_cents
        records.append(
            {
                "filename": info.filename,
                "period": info.period,
                "period_text": info.period_text,
                "report_format": info.report_format,
                "header_valid": info.header_valid,
                "selected": info.selected,
                "selection_reason": info.selection_reason,
                "hs2_rows": info.counts.get(2, 0),
                "hs4_rows": info.counts.get(4, 0),
                "hs6_rows": info.counts.get(6, 0),
                "hs8_rows": info.counts.get(8, 0),
                "country_rows": info.country_rows,
                "chapters": ",".join(sorted(info.chapters)),
                "reported_total_usd": None if info.reported_total_cents is None else info.reported_total_cents / 100,
                "hs8_sum_usd": hs8_sum / 100,
                "top_level_total_gap_usd": None if total_gap is None else total_gap / 100,
                "sha256": info.sha256,
                "modified_at": info.modified_at,
                "parse_errors": " | ".join(info.parse_errors),
            }
        )
    return records


def write_validation(
    output_dir: Path,
    infos: list[WorkbookInfo],
    issues: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(source_manifest(infos)).to_csv(output_dir / "source_manifest.csv", index=False)
    pd.DataFrame(issues, columns=["severity", "issue_code", "period", "source_file", "message"]).to_csv(
        output_dir / "qa_issues.csv", index=False
    )
    (output_dir / "qa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    selected = [i for i in infos if i.selected]
    lines = [
        "# EPB source validation",
        "",
        f"Status: **{summary['status']}**",
        f"Authoritative sources selected: **{len(selected)}** for **{len(EXPECTED_MONTHS)}** months.",
        "",
        "## June 2026 source selection",
        "",
    ]
    june = [i for i in infos if i.period == "2026-06"]
    for item in june:
        lines.append(f"- `{item.filename}` — {item.report_format}; {item.selection_reason}; {item.counts.get(8, 0)} HS8 rows.")
    lines.extend(["", "## QA issues", ""])
    for item in issues:
        lines.append(f"- **{item['severity'].upper()}** `{item['issue_code']}` {item.get('period', '')}: {item['message']}")
    (output_dir / "validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _month_label(month: str) -> str:
    return datetime.strptime(month, "%Y-%m").strftime("%b %Y")


def _sector_value(monthly: list[dict[str, Any]], month: str, field: str) -> float | None:
    rows = [row for row in monthly if row["month"] == month]
    if field in {"monthly_usd", "monthly_usd_million"}:
        values = [row[field] for row in rows]
        return sum(values) if values and all(value is not None for value in values) else None
    totals = {
        item: _sector_value(monthly, item, "monthly_usd")
        for item in EXPECTED_MONTHS
    }
    current = totals[month]
    index = EXPECTED_MONTHS.index(month)
    prior = None if index == 0 else totals[EXPECTED_MONTHS[index - 1]]
    if field == "share_pct":
        return 100.0 if current not in (None, 0) else None
    if current is None or prior is None:
        return None
    change = current - prior
    if field == "mom_change_usd":
        return change
    if field == "mom_pct":
        return change / prior * 100 if prior > 0 else None
    return None


def _matrix(monthly: list[dict[str, Any]], field: str, scale: float = 1.0) -> pd.DataFrame:
    rows = []
    groups = sorted({row["product_group"] for row in monthly})
    lookup = {(row["product_group"], row["month"]): row.get(field) for row in monthly}
    for group in groups:
        record: dict[str, Any] = {"Product group": group}
        for month in EXPECTED_MONTHS:
            value = lookup.get((group, month))
            record[_month_label(month)] = "NA" if value is None else value / scale
        rows.append(record)
    total_record: dict[str, Any] = {"Product group": "IN-SCOPE TOTAL"}
    for month in EXPECTED_MONTHS:
        value = _sector_value(monthly, month, field)
        total_record[_month_label(month)] = "NA" if value is None else value / scale
    rows.append(total_record)
    return pd.DataFrame(rows)


def write_report(
    output_dir: Path,
    chart_dir: Path,
    infos: list[WorkbookInfo],
    issues: list[dict[str, Any]],
    scope: list[dict[str, str]],
    detail: list[dict[str, Any]],
    monthly: list[dict[str, Any]],
    provisional: bool,
    scope_hash: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    charts = write_png_charts(monthly, chart_dir)
    monthly_df = pd.DataFrame(monthly)
    detail_df = pd.DataFrame(detail)
    scope_df = pd.DataFrame(scope)
    sources_df = pd.DataFrame(source_manifest(infos))
    issues_df = pd.DataFrame(issues)
    monthly_df.to_csv(output_dir / "monthly_by_product.csv", index=False)
    monthly_df[["month", "product_group", "mom_change_usd", "mom_pct", "mom_reason", "qa_status"]].to_csv(
        output_dir / "mom_by_product.csv", index=False
    )
    detail_df.to_csv(output_dir / "hs8_monthly_detail.csv", index=False)
    sources_df.to_csv(output_dir / "source_manifest.csv", index=False)
    issues_df.to_csv(output_dir / "qa_issues.csv", index=False)
    period_totals = _period_totals(monthly)
    pd.DataFrame(period_totals).to_csv(output_dir / "period_totals_by_product.csv", index=False)

    usd = _matrix(monthly, "monthly_usd")
    usd_m = _matrix(monthly, "monthly_usd_million")
    mom_pct = _matrix(monthly, "mom_pct")
    mom_usd = _matrix(monthly, "mom_change_usd")
    share = _matrix(monthly, "share_pct")
    report_path = output_dir / "epb_power_equipment_exports_2025_07_to_2026_10.xlsx"
    with pd.ExcelWriter(report_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        title_fmt = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#17365D"})
        sub_fmt = workbook.add_format({"bold": True, "font_size": 12, "font_color": "#1F4E78"})
        warn_fmt = workbook.add_format({"bold": True, "font_color": "#9C0006", "bg_color": "#FFC7CE", "text_wrap": True})
        note_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})
        executive = workbook.add_worksheet("Executive Summary")
        writer.sheets["Executive Summary"] = executive
        executive.set_column("A:A", 28)
        executive.set_column("B:B", 105)
        executive.write("A1", "EPB Power-Equipment Export Analysis", title_fmt)
        if provisional:
            executive.merge_range("A3:B4", PROVISIONAL_WARNING, warn_fmt)
        executive.write("A6", "Reporting period", sub_fmt)
        executive.write("B6", "July 2025–October 2026 (16 calendar months)")
        executive.write("A7", "Measure", sub_fmt)
        executive.write("B7", "Export value in USD; monthly figures are first differences of EPB FYTD cumulative reports.")
        executive.write("A8", "June 2026", sub_fmt)
        executive.write("B8", "Authoritative 8 Digit sheet from Product-wise Export (Goods); truncated detailed workbook used only for overlap QA.")
        executive.write("A9", "Scope status", sub_fmt)
        executive.write("B9", "Draft—requires human approval" if provisional else "Approved")
        executive.write("A10", "Interpretation caveat", sub_fmt)
        executive.write("B10", "Signed monthly deltas may include historical revisions/reclassification and are not independently observed shipments.", note_fmt)
        executive.write("A11", "QA issues", sub_fmt)
        executive.write("B11", f"{sum(i.get('severity') == 'critical' for i in issues)} critical; {sum(i.get('severity') == 'warning' for i in issues)} warnings")
        executive.write("A12", "Scope file SHA-256", sub_fmt)
        executive.write("B12", scope_hash)
        executive.write("A13", "Generated", sub_fmt)
        executive.write("B13", datetime.now(ZoneInfo("Asia/Dhaka")).isoformat())
        executive.write("A14", "Code version", sub_fmt)
        executive.write("B14", __version__)
        executive.write("A16", "Source attribution", sub_fmt)
        executive.write("B16", "Export Promotion Bureau (EPB); underlying data source: NBR; EPB Commodity-wise Detailed Data and Product-wise Export (Goods); downloaded by user.", note_fmt)
        executive.write("A19", "16-month coverage and totals", sub_fmt)
        totals_frame = pd.DataFrame(period_totals)
        totals_frame.to_excel(writer, sheet_name="Executive Summary", index=False, startrow=19)
        executive.set_column("C:D", 24)

        sheets = {
            "Monthly USD": (usd, "#,##0.00;[Red]-#,##0.00;0.00"),
            "Monthly USD Million": (usd_m, "0.000;[Red]-0.000;0.000"),
            "MoM Growth %": (mom_pct, "0.0%;[Red]-0.0%"),
            "MoM Change USD": (mom_usd, "#,##0.00;[Red]-#,##0.00;0.00"),
            "Monthly Product Share %": (share, "0.0%"),
        }
        # Percent fields are stored as percentage points, so convert to Excel fractions.
        for column in mom_pct.columns[1:]:
            mom_pct[column] = mom_pct[column].map(lambda x: x / 100 if isinstance(x, (int, float)) else x)
        for column in share.columns[1:]:
            share[column] = share[column].map(lambda x: x / 100 if isinstance(x, (int, float)) else x)
        for sheet_name, (frame, number_format) in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            sheet = writer.sheets[sheet_name]
            sheet.freeze_panes(1, 1)
            sheet.autofilter(0, 0, len(frame), len(frame.columns) - 1)
            sheet.set_column(0, 0, 38)
            sheet.set_column(1, len(frame.columns) - 1, 13, workbook.add_format({"num_format": number_format}))
            if sheet_name == "MoM Growth %":
                sheet.conditional_format(1, 1, len(frame), len(frame.columns) - 1, {"type": "cell", "criteria": ">", "value": 0, "format": workbook.add_format({"font_color": "#006100", "bg_color": "#C6EFCE"})})
                sheet.conditional_format(1, 1, len(frame), len(frame.columns) - 1, {"type": "cell", "criteria": "<", "value": 0, "format": workbook.add_format({"font_color": "#9C0006", "bg_color": "#FFC7CE"})})

        detail_df.to_excel(writer, sheet_name="HS8 Detail", index=False)
        scope_df.to_excel(writer, sheet_name="Scope & Exclusions", index=False)
        sources_df.to_excel(writer, sheet_name="Sources & QA", index=False, startrow=1)
        issues_start = len(sources_df) + 5
        issues_df.to_excel(writer, sheet_name="Sources & QA", index=False, startrow=issues_start)
        for name in ("HS8 Detail", "Scope & Exclusions", "Sources & QA"):
            sheet = writer.sheets[name]
            sheet.freeze_panes(2 if name == "Sources & QA" else 1, 0)
            sheet.set_column(0, max(0, (detail_df if name == "HS8 Detail" else scope_df if name == "Scope & Exclusions" else sources_df).shape[1] - 1), 18)
        writer.sheets["Scope & Exclusions"].set_column(4, 5, 55)
        writer.sheets["HS8 Detail"].set_column(4, 4, 50)
        sources_sheet = writer.sheets["Sources & QA"]
        sources_sheet.write(0, 0, "Source inventory and selection", sub_fmt)
        sources_sheet.write(issues_start - 1, 0, "QA issues", sub_fmt)

        chart_sheet = workbook.add_worksheet("Charts")
        writer.sheets["Charts"] = chart_sheet
        chart_sheet.insert_image("A1", str(charts[0]), {"x_scale": 0.50, "y_scale": 0.50})
        chart_sheet.insert_image("A41", str(charts[1]), {"x_scale": 0.72, "y_scale": 0.72})
        chart_sheet.insert_image("A71", str(charts[2]), {"x_scale": 0.72, "y_scale": 0.72})

    _write_briefing(output_dir, scope, monthly, issues, provisional)
    return report_path


def _write_briefing(
    output_dir: Path,
    scope: list[dict[str, str]],
    monthly: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    provisional: bool,
) -> None:
    included = [row for row in scope if row.get("include", "").upper() == "Y"]
    negative_count = sum("negative_revision" in row["qa_status"] for row in monthly)
    lines = ["# EPB power-equipment exports: briefing summary", ""]
    if provisional:
        lines.extend([f"> **{PROVISIONAL_WARNING}**", ""])
    lines.extend(
        [
            "## Method",
            "",
            "Monthly USD values are net first differences of fiscal-year-to-date EPB cumulative HS8 values. July is the first observation in each fiscal year; MoM comparison continues across the June–July boundary.",
            "",
            "June 2026 uses the Product-wise Export (Goods) workbook's `8 Digit` product subtotals. The truncated detailed June workbook is used only for cross-validation.",
            "",
            "## Scope",
            "",
            f"The conservative draft includes {len(included)} exact HS8 codes across {len({row['product_group'] for row in included})} product groups. It is not an official sector definition until a human reviewer changes included decisions to `approved` in `config/hs_scope.csv`.",
            "",
            "## Caveats",
            "",
            f"- {negative_count} product-group/month records contain one or more negative HS8 first differences and require revision-aware interpretation.",
            f"- QA log contains {sum(i.get('severity') == 'critical' for i in issues)} critical items and {sum(i.get('severity') == 'warning' for i in issues)} warnings.",
            "- A first difference can combine current exports with EPB/NBR historical revisions or reclassification; it is labelled a net delta rather than independently observed shipments.",
            "- HS nomenclature changes can impair comparisons across years; the exact code/description audit table must be retained.",
            "",
            "## Source",
            "",
            "Export Promotion Bureau (EPB); underlying data source: NBR; EPB Commodity-wise Detailed Data and Product-wise Export (Goods); downloaded by user.",
            "Dataset page: https://epb.gov.bd/views/epb-export-data",
        ]
    )
    (output_dir / "briefing_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _period_totals(monthly: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in sorted({row["product_group"] for row in monthly}):
        rows = [row for row in monthly if row["product_group"] == group]
        available = [row for row in rows if row["monthly_usd"] is not None]
        valid = [
            row
            for row in rows
            if row["monthly_usd"] is not None
            and "negative_revision" not in row["qa_status"]
            and "incomplete_source" not in row["qa_status"]
        ]
        complete = len(valid) == len(EXPECTED_MONTHS)
        records.append(
            {
                "product_group": group,
                "valid_months": len(valid),
                "coverage": f"{len(valid)}/{len(EXPECTED_MONTHS)}",
                "complete_period_total_usd": sum(row["monthly_usd"] for row in valid) if complete else "NA",
                "available_net_delta_sum_usd": sum(row["monthly_usd"] for row in available),
                "total_status": "complete" if complete else "partial_revision_qualified",
            }
        )
    return records

