# Data dictionary

## `hs8_monthly_detail.csv`

- `month`: calendar month, `YYYY-MM`.
- `fiscal_year`: Bangladesh reporting FY label.
- `hs8`, `product_group`, `description`: auditable classification fields.
- `cumulative_cents`, `monthly_cents`: canonical integer-cent measures.
- `cumulative_usd`, `monthly_usd`: display/export conveniences.
- `qa_status`, `issue_reason`: validity and interpretation state.
- `source_file`, `source_row`: source traceability.
- `calculation`: July FYTD or current-minus-prior FYTD.

## `monthly_by_product.csv`

One product group/month row with USD, USD million, MoM change, MoM percentage, share, reason, and QA status. NA values are never exported as zero.

## Diagnostics

`source_manifest.csv` records format, A3 period, selection, row counts, chapters, totals, checksums, and file modification time. `qa_issues.csv` is the full machine-readable issue log; `qa_summary.json` is the gate result.

