# EPB power-equipment exports

This local-first Python project converts EPB fiscal-year-to-date commodity reports into an auditable monthly panel for July 2025–October 2026. It analyzes export **value in USD**, not quantity.

The June 2026 authority is the product-wise workbook's `8 Digit` sheet. `data/2025_07_2026_06.xlsx` is deliberately retained only for its 1,110-code overlap check because its detailed hierarchy stops before Chapters 85 and 90.

## Setup

Ubuntu/WSL:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m epb_power inspect
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m epb_power inspect
```

## Commands

```bash
.venv/bin/python -m epb_power inspect
.venv/bin/python -m epb_power validate
.venv/bin/python -m epb_power scope-candidates
.venv/bin/python -m epb_power report
.venv/bin/python -m epb_power report --allow-incomplete --allow-draft-scope
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
```

`report` is strict: it will not publish while included rows in `config/hs_scope.csv` remain `draft`, an authoritative month is missing, or material in-scope completeness fails. The two `--allow-*` options create visibly provisional output and never silently waive warnings.

## Human scope review

`config/hs_scope_candidates.csv` is regenerated from the union of observed candidate HS8 codes. `config/hs_scope.csv` is created once and then preserved. Review every row, edit `include`, `product_group`, `decision_note`, and change `review_status` to `approved` only after an accountable human decision. Generic converters, batteries, low-voltage conductors and ambiguous accessories default to exclusion.

## Interpretation

Within a fiscal year, monthly value is current cumulative USD minus prior-month cumulative USD; July equals its own cumulative value. June-to-July is not subtracted because the FY resets, but MoM compares the independently derived months. Negative first differences are retained and flagged: they can reflect corrections, exchange-rate restatement or reclassification and are not proven negative physical shipments.

See [methodology](docs/methodology.md), [data dictionary](docs/data_dictionary.md), and [limitations](docs/limitations_and_review.md).

