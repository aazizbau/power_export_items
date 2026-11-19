# Codex task: Build a reproducible EPB power-equipment export analysis pipeline (revised: June product-wise source)

Act as a senior Python data engineer, trade-data analyst, and QA engineer. Implement a complete, maintainable, local-first Python project **inside the currently open VS Code workspace**. Do not merely outline a solution: create the actual files, execute the pipeline as far as possible, run tests, and report precise results, blockers, and commands. Do not move, delete, rename, overwrite, or modify any original `.xlsx` files in `./data/`, including the supplemental June product-wise file. Do not commit or push to Git unless I explicitly ask.

## 1. Objective and reporting period

Analyze monthly **export VALUE in USD** (not physical quantity) for a carefully defined, auditable list of Bangladesh power-sector-related equipment between **July 2025 and October 2026 inclusive (16 months)**, using Export Promotion Bureau (EPB) commodity-wise detailed export reports. Generate for each approved product category and exact 8-digit HS code:

1. Monthly exports (USD and USD million) for all 16 calendar months.
2. Month-over-month (MoM) absolute change in USD and percentage increase/decrease, compared with the **immediately preceding calendar month**, including across the June-to-July fiscal-year boundary when source data permit.
3. Product category's share of total in-scope power-equipment exports in each month (%).
4. A 16-month cumulative total **only when every relevant month's data are valid**; otherwise label partial totals with coverage and mark the complete-period total unavailable.
5. A well-formatted meeting-ready Excel workbook, charts, CSV exports, an executive summary, source provenance, and detailed QA diagnostics.

Reporting periods: FY2025-26 (July 2025–June 2026) and FY2026-27 (July–October 2026). Each workbook contains **fiscal-year-to-date cumulative** values, not independent monthly values. Therefore calculate monthly values by taking first differences within each fiscal year. For the first July in each fiscal year, the monthly value equals that July file's cumulative value. Do **not** subtract June 2026 cumulative values from July 2026 cumulative values, as the fiscal year resets; but for MoM percentage compare the independently calculated July 2026 monthly value with the independently calculated June 2026 monthly value, if both exist and are trustworthy.

## 2. Existing files and verified source structure

The **original 16 files** are expected in `./data/` with the following names; do not assume the earlier `2025-07.xlsx` convention. **One additional June 2026 product-wise workbook must also be copied to `./data/`**, preferably named `2025_07_2026_06_productwise.xlsx`. The supplemental file may retain its original download name; identify it using workbook metadata, worksheet structure, and period text instead of relying only on the filename:

```
data/2025_07.xlsx
data/2025_07_08.xlsx
data/2025_07_09.xlsx
data/2025_07_10.xlsx
data/2025_07_11.xlsx
data/2025_07_12.xlsx
data/2025_07_2026_01.xlsx
data/2025_07_2026_02.xlsx
data/2025_07_2026_03.xlsx
data/2025_07_2026_04.xlsx
data/2025_07_2026_05.xlsx
data/2025_07_2026_06.xlsx
data/2026_07.xlsx
data/2026_07_08.xlsx
data/2026_07_09.xlsx
data/2026_07_10.xlsx
```

I inspected the uploaded workbooks; independently verify their metadata and contents during implementation.

### 2A. Fifteen complete-period detailed workbooks and the original June detailed workbook

- The **detailed** format has one sheet named `Worksheet 1`, A1 `Export Promotion Bureau`, A2 `Report: Commodity wise Detailed Data`, and A3 containing the period, e.g. `Period: July-October 2026-27`.
- Row 5 contains `HS Code` in A5 and `USD` in B5.
- The A column contains indented hierarchy rows whose code is followed by a colon, e.g. `85: ...`, `8504: ...`, `850421: ...`, `85042100: ...`. The B column contains FY-to-date **raw USD** values for those rows.
- The 2-, 4-, 6-, and 8-digit levels are **nested subtotals**, and must never be summed together. For reporting choose only explicitly included HS8 codes. Preserve leading zeros.
- Final lines can include `Dig Count`, `Total`, `USD Rate`, and `Data Source NBR`. They are non-product metadata; retain the overall Total for source QA.
- **Original June 2026 detailed workbook `2025_07_2026_06.xlsx` is truncated**: its HS hierarchy ends at Chapter 74 and Chapter 85/90 are absent; it has 1,110 HS8 entries. Its overall Total nevertheless reads USD 48,001,914,791.61. DO NOT use its missing Chapter 85/90 entries as zero, and DO NOT use it as the production source for June exports.

### 2B. NEW, VERIFIED authoritative June 2026 product-wise workbook

The user has supplied a **Product-wise Export (Goods) workbook for July 2025–June 2026**, which successfully recovers the missing June commodity details. Place it in `./data/`, ideally as `data/2025_07_2026_06_productwise.xlsx`. It is a separate **supplementary source for the SAME period** as the original truncated detailed workbook, not a 17th month.

Actual verified structure:

- Four worksheets: `2 Digit`, `4 Digit`, `6 Digit`, `8 Digit`.
- Read only the worksheet **`8 Digit`** for authoritative June 2026 HS8 figures.
- `A1 = Export Promotion Bureau`, `A2 = Report: Commodity-wise Data of Countries`, `A3 = Period: July-June 2025-26`, row 5 `A=HS Code`, `B=Country`, `C=USD`.
- A **product subtotal row** has a literal 8-digit HS code and description in column A (e.g. `85042100: ...`), **blank country in column B**, and cumulative export **USD in column C**. Following rows usually have blank A, `XX: Country` in B, and country-specific USD in C. **Do not sum those country rows into the subtotal.** They may be used for optional independent reconciliation with a documented rounding tolerance based on the number of countries (observed maximum absolute difference about USD 0.06).
- There are **2,399 unique HS8 product subtotal rows**, including Chapter 85 and Chapter 90 products. The sum of those product subtotals is **USD 48,001,914,791.70**; the EPB grand total is **USD 48,001,914,791.61**, an **USD 0.09** reconciliation difference caused by cent-level rounding across thousands of rows. Use an explicit documented absolute tolerance for overall totals, not exact float equality.
- The product-wise June data and original truncated detailed June data share **1,110 HS8 codes**, and all 1,110 shared-code cumulative USD values **agree exactly**. Implement a test/audit asserting this overlap consistency within cent tolerance.
- This restores the data needed for deriving **June 2026** monthly exports (June FY-to-date product-wise value minus May FY-to-date detailed value) and **July 2026** MoM change (July actual monthly exports against June actual monthly exports), subject to HS coverage, negative revisions, and scope QA.

**Source selection rules (REQUIRED):**

1. Recognize *report format* by sheet names + headers: `detailed` (`Worksheet 1`, amount in B) versus `product_wise_country` (`8 Digit`, amount in C).
2. Recognize *period* from A3 and cross-check filename if its filename encodes the period. A nonstandard downloaded filename must not make a valid source inaccessible.
3. For June 2026, explicitly prioritize the **complete product-wise HS8 subtotal** data over the truncated detailed workbook. Mark the original as `supplemental_truncated_not_selected` and retain it solely to compare the 1,110 overlapping rows and its grand total. **Do not aggregate/sum both workbooks together.**
4. For the remaining 15 months, use the respective detailed workbooks. Thus the final panel has exactly **16 months**, while source inventory can have **17 workbook files**.
5. A *real duplicate* is two competing complete sources for the same report type and period with conflicting figures. Do not misclassify the two legitimate June formats as a duplicate fatal error.
6. If the June product-wise workbook is absent, corrupt, lacks the `8 Digit` sheet, has no Chapter 85 records, or fails severe reconciliation, **then** strict mode must fail; `--allow-incomplete` may produce an explicitly labeled provisional report with missing June and July MoM. If the verified product-wise data passes QA and the HS scope is approved, **do not fail strict mode merely because the unused detailed June file is truncated**.
7. The product-wise workbook also contains country detail, which can enable optional country-level analysis in a separate feature. It is **not** required for monthly product-level reporting and must never be double-counted.

**Further QA caveat:** Some detailed monthly sources may have incomplete HS8 coverage despite carrying a full reported grand total, especially within certain HS headings. For example, in the May 2026 detailed workbook, the HS4 `8541` subtotal exceeds the sum of its available HS8 children by approximately USD 4,230.27; the October 2026 detailed workbook's `8541` HS4/HS8 gap is about USD 28,192.47. These differences need investigation when selecting solar products. Distinguish **scope-relevant** coverage gaps from gaps elsewhere in the full national export file. Do not treat an unrelated national-total mismatch as proof that all selected HS8 equipment categories are unusable; equally, do not conceal missing HS8 values in approved headings.

## 3. Product scope (conservative, human-auditable)

Do NOT use all of HS Chapter 85 as power-sector equipment and do NOT blindly include all 8-digit codes starting with a broad heading. Define carefully reviewed groups and record exact codes, commodity descriptions, inclusion decisions, uncertainty, and supporting rationale.

Suggested **candidate** families, not automatic approval:

- Transformers: 850421, 850422, 850423, 850431, 850432, 850433, 850434 (find exact 8-digit children).
- Switchgear/protection: selected electrical-power equipment within 8535 and 8536 (exclude irrelevant accessories by reviewing descriptions).
- Distribution/control panels: selected 8537 children.
- Power cables and conductors: selected 8544 children; exclude telecom/optical-fibre and unrelated cabling.
- Solar PV cells/modules: relevant precise 8541 children, particularly 854143 where present; do not assume absent codes have exports.
- Industrial/energy-storage batteries: relevant 8507 children; distinguish automotive starter batteries from stationary/industrial categories where the HS description permits; leave ambiguous codes unapproved.
- Grid-relevant inverters/converters: selected 850440 children **only when the description supports the classification**; do not label all static converters as solar inverters.
- Electricity meters: relevant 902830 children where present.

Build `config/hs_scope_candidates.csv` automatically by scanning all usable workbooks for exact 8-digit codes in these families, unioned across months, with `hs8`, `description`, `proposed_group`, `observed_files_or_months`, `suggested_include` (default `N` for uncertain entries), `reason`, and `needs_review`. Provide `config/hs_scope.csv` as a maintained decision table with `hs8`, `product_group`, `include` (`Y`/`N`), `review_status` (`approved`/`draft`), `decision_note`, and `description`. A user can review and change these without modifying Python. Codex may propose a **conservative draft mapping** based on descriptions, but DO NOT falsely claim it has been officially approved. Strict publishable output should require an approved scope; an explicitly labeled provisional/draft option can run for exploration. Validate no duplicated included HS8 codes across groups, no contradictory statuses, no unparseable codes. Include an audit table of excluded/uncertain codes. If there are zero approved codes, provide specific next steps rather than inventing totals.

Use a clear distinction between **export value of goods in selected HS codes** and the entire national electrical-products export sector. Check for HS code changes or reclassification across years and explain that such changes may break long-run comparability.

## 4. Parser, calculation, and QA rules

- Use Python 3.11+ with type hints, a package in `src/`, structured logging, pathlib, pytest, pandas, openpyxl (read-only input), and xlsxwriter (styled output). Use the standard library `decimal.Decimal` or another carefully justified currency-safe method; normalize source currency values to **USD cents** at ingestion. Display USD million by dividing by 1,000,000, without changing the stored raw USD amounts.
- Discover all Excel files in `data/`, recognize both report formats by sheet/header, extract their periods from row 3, and map to 16 expected end-months. Permit **17 source files for 16 months** because two different June formats coexist. Cross-check filenames where recognizable, but allow the new product-wise June workbook to retain a nonstandard downloaded name. Select **exactly one authoritative source per period** and log source precedence and reasons. Detect real duplicate conflicts, missing workbooks, unrecognized formats, and invalid headers. Do not require renaming existing files.
- Parse the detailed worksheet column A using an anchored regex extracting exactly 2, 4, 6, or 8 digit codes before a colon. Parse the product-wise `8 Digit` worksheet **product subtotal rows only**, requiring an 8-digit code in A and blank Country B, and read the value from C. Record country rows separately for QA only. Preserve leading zeros and source row, hierarchy level, description, original value, format, selected/rejected source, period, and cumulative USD. HTML entities in descriptions may be decoded for display but raw text must be traceable.
- Exclude `Dig Count`, `Total`, metadata rows, and all aggregated 2/4/6-digit rows from HS8-level sums. Use the higher levels **only** for coverage/reconciliation QA. Check duplicates within each file and differences in descriptions for the same code across files.
- Independently check: each format's reported Total against its highest complete available commodity level; the June product-wise total against its HS8 subtotal sum (USD 0.09 rounding difference is acceptable); all 1,110 June overlapping codes across sources; selected-code coverage; 6-digit parents versus 8-digit children where coverage is claimed; relevant HS4/HS6 gaps; missing entire HS8 families; negative/abruptly changing cumulative values. Report gaps instead of filling them. Distinguish source-wide/in-scope issues; flag material anomalies for publishable reporting.
- Build a **union** of all included HS8 codes across all months (not an intersection). For a valid cumulative report, a code not previously observed can indicate zero cumulative export before its first appearance. If a previously positive code disappears from a subsequent cumulative file, **flag it**, investigate and avoid assuming a valid zero when completeness or classification is questionable. Never interpret missing codes in an incomplete source as zero.
- Within each FY, monthly = cumulative_at_end_of_month - cumulative_at_end_of_previous_month; first July = cumulative July. Do this at HS8 level, then aggregate validated monthly HS8 values into product groups (not vice versa when code-level anomalies need audit). Ensure each month/group is traceable to one or two source files and rows.
- A negative monthly difference is possible because of revisions, exchange-rate-based restatements, reclassifications, or faulty data. Verified May→June data contain numerous small negative HS8 deltas even though June is overall greater than May; for example HS8 `85042100` changes from USD 23,828.26 (May FYTD) to USD 23,820.28 (June FYTD). **Do not clamp negative to zero, do not invent positive shipments, and do not automatically assume physical negative export.** Expose signed diffs, flag them, record plausible source-revision causes as hypotheses (not proven facts), and separate `net_delta_of_cumulative_reports` from verified independently observed monthly shipment values. The report must state that first differences can reflect both exports and historical revisions; consider excluding material unresolved negative values from official aggregates or prominently qualify the figures.
- MoM change USD = monthly_value(t) - monthly_value(t-1). MoM % = 100 * change / monthly_value(t-1) **only if** both monthly values are valid and the previous value is strictly positive. If previous = 0 or missing, return `NA` with an explanation (`new_activity`, `zero_base`, `missing_prior_month`, etc.). Never report infinite growth. For July 2025 MoM is NA because June 2025 is not in the dataset. MoM runs continuously across FY boundaries if both valid monthly amounts exist.
- When an input is missing/invalid, propagate NA into derived fields. Distinguish `no_export_evidence`, `confirmed_zero`, `not_applicable`, `missing_source`, `incomplete_source`, `ambiguous_hs`, `negative_revision`, and `needs_review`. Include `qa_status` and a human-readable issue reason for each affected record.
- Add reproducibility metadata: input filenames, workbook A3 period, SHA-256 checksums, modification times (informational), scope file hash/version, run timestamp with timezone, code version, and calculation definitions. Never use source-provided workbook creation time as the export month.
- Implement the strict/provisional rules as explicit functions, not scattered special cases.

## 5. Required repository scaffold

Create these **real** files/folders (adapt reasonably as needed; preserve any existing user files):

```
./
├── .venv/                          # create locally; do NOT commit
├── .gitignore
├── .python-version                # optional, Python 3.11+
├── AGENTS.md                      # Codex/project rules and QA gates
├── README.md                      # setup, method, commands, troubleshooting
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml                 # pytest/ruff config, optional package metadata
├── .vscode/
│   ├── settings.json
│   ├── tasks.json
│   └── launch.json                 # optional helpful debug command
├── config/
│   ├── settings.toml              # Python stdlib tomllib-compatible
│   ├── hs_scope.csv               # reviewed/draft explicit mapping
│   └── hs_scope_candidates.csv    # generated candidates
├── data/                          # preserve 16 originals and new June product-wise workbook
│   ├── ... 16 original files ...
│   └── 2025_07_2026_06_productwise.xlsx  # recommended name; original download name also supported
├── src/epb_power/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── discovery.py
│   ├── parser.py
│   ├── scope.py
│   ├── calculations.py
│   ├── quality.py
│   ├── reporting.py
│   ├── charts.py
│   └── provenance.py
├── tests/
│   ├── conftest.py
│   ├── test_discovery.py
│   ├── test_parser.py
│   ├── test_calculations.py
│   ├── test_scope.py
│   ├── test_quality.py
│   └── test_integration.py
├── docs/
│   ├── methodology.md
│   ├── data_dictionary.md
│   └── limitations_and_review.md
├── outputs/                       # generated; gitignored
│   ├── diagnostics/
│   ├── provisional/
│   ├── final/
│   └── charts/
└── logs/                          # generated; gitignored
```

`.gitignore` must ignore `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, IDE/OS junk, `.env`, `outputs/`, `logs/`, and **raw downloaded data Excel files** (but keep `data/` folder via `.gitkeep` if desired). Do not accidentally ignore reviewed `config/hs_scope.csv`, docs, tests, or code. Use `.vscode/settings.json` to select local `.venv` interpreter; do not hardcode a computer-specific absolute path. Do not write proprietary/raw EPB source workbooks into Git history.

Create `.venv` via `python -m venv .venv` (try an installed Python 3.11+ interpreter), install `requirements.txt` and `requirements-dev.txt`, and run tests. Support VS Code on Windows PowerShell and Ubuntu/WSL, with platform-aware shell commands. If local environment or package access prevents installation, still implement the project and clearly report the exact command and error; do not pretend that installation or tests succeeded.

## 6. CLI and execution behavior

Provide robust, `argparse`-based entry points supporting at least:

```
python -m epb_power inspect
python -m epb_power validate
python -m epb_power scope-candidates
python -m epb_power report                  # STRICT: use verified product-wise June; fail only for genuine QA blockers or unapproved scope
python -m epb_power report --allow-incomplete --allow-draft-scope
python -m epb_power report --output-dir outputs/provisional
python -m pytest -q
python -m ruff check .
```

Commands should discover the project root robustly (or accept `--data-dir`, `--config-dir`, and `--output-dir`), work when run from VS Code workspace root, and produce friendly help/error text. `inspect` prints each workbook's metadata, report format, row counts by HS level, chapter/code coverage, grand-total reconciliation, chosen source per period, and missing/unexpected months; both June files must appear, with only the product-wise June file selected for calculations. `validate` writes `outputs/diagnostics/source_manifest.csv`, `qa_issues.csv`, `qa_summary.json`, and a readable Markdown validation summary even when critical errors exist. `scope-candidates` generates candidates without overwriting a user's existing reviewed scope. `report` always runs validation first, stops before a final report on critical issues in strict mode, and emits a prominently watermarked provisional report only if explicitly requested. Never claim success unless files were actually created and checked.

## 7. Required outputs

Create a polished, ministry-meeting-ready Excel workbook named `epb_power_equipment_exports_2025_07_to_2026_10.xlsx` (in `outputs/final` when validated, or `outputs/provisional` if explicitly allowed), containing:

1. `Executive Summary` — date range, data quality status, scope status, currency/unit, key validated trends, missing months, and clear provisional warning if needed.
2. `Monthly USD` — categories as rows and 16 calendar months as columns; USD export values and sector total if all groups valid; missing values displayed as `NA`, not 0.
3. `Monthly USD Million` — same in USD million, with three decimals (underlying USD preserved).
4. `MoM Growth %` — monthly percent increase/decrease per group, with appropriate conditional formatting and undefined values labeled `NA`.
5. `MoM Change USD` — absolute month-on-month difference.
6. `Monthly Product Share %` — each approved category's share of the valid in-scope total, when all relevant categories are valid.
7. `HS8 Detail` — one row per period and included HS8 with code, group, description, cumulative USD, derived monthly USD, status, source filename, source row, and calculation provenance.
8. `Scope & Exclusions` — classification rationale and approval status; clearly identify ambiguous/excluded categories.
9. `Sources & QA` — source-period mapping, file hash, chapter coverage, grand-total consistency, critical alerts, affected months, footnotes.
10. `Charts` — readable product-group monthly export trend and (if valid) MoM growth chart; do not chart NA as zero. Optional separate chart PNGs.

Also export tidy analysis CSVs (`monthly_by_product.csv`, `mom_by_product.csv`, `hs8_monthly_detail.csv`, `source_manifest.csv`, `qa_issues.csv`) with machine-friendly ISO month identifiers `YYYY-MM` and unambiguous units. Write a short **`briefing_summary.md`** stating methodology, reviewed product scope, notable findings **only supported by validated data**, prominent caveats, and source attribution: `Export Promotion Bureau (EPB); underlying data source: NBR; EPB Commodity-wise Detailed Data and Product-wise Export (Goods); downloaded by user`. Include the dataset page `https://epb.gov.bd/views/epb-export-data`. Do not manufacture figures or unofficial descriptions.

Use a professional, readable workbook style: frozen top row and label column, filters, month headings formatted `Jul 2025`, grouped headings, source/QA notes, sensible number formats, conditional coloring for MoM up/down, no clipped labels, and explicit USD versus USD million units. Allow Bengali labels in README/executive summary if easy, but preserve machine-readable English identifiers.

## 8. Tests and acceptance criteria

Write deterministic unit tests using **small synthetic Excel files created by tests**, plus an optional local-file integration test against `data/` (skip only if data unavailable). Cover:

- Exact 16-month filename-to-period mapping and A3/header validation.
- Parsing the 2/4/6/8 hierarchy, leading zeros, colon-delimited descriptions, non-data summary lines, cents, and duplicate code detection.
- Detecting truncation in the original June detailed workbook while selecting the complete June product-wise workbook; validating its four-sheet format, HS8 product subtotal rows, country rows, columns A/B/C, 2,399 HS8 rows, Chapter 85/90 presence, 0.09 USD grand-total tolerance, and 1,110-row overlap reconciliation. Distinguish the two legitimate June formats from a real conflicting duplicate.
- Union of HS8 codes across months, missing versus verified zero, scope approvals and collision detection.
- Month arithmetic: July cumulative USD 100, August cumulative USD 130 gives August monthly USD 30 (not 130); subsequent FY July cumulative USD 50 gives July monthly USD 50 (not a difference from previous FY June).
- Correct MoM change and percent; zero/missing base yields NA. With valid supplemental June product-wise data, June monthly values and July 2026 MoM should be calculated when underlying HS8 values are complete and trusted. As a separate failure-path test, remove the supplemental workbook and assert strict-mode failure and provisional NA for June and July MoM.
- Negative revision events are flagged, never silently replaced by zero.
- Strict mode fails on absent/unusable authoritative June product-wise source, material in-scope QA blockers, and draft scope; but it **must not fail solely on the unused truncated detailed June file** when product-wise June is valid. Explicit provisional mode has the exact warning in both Excel and Markdown when blockers remain.
- CSV/Excel output schemas, 16 month columns, no duplicate HS8 group assignment, USD-to-million conversion, and provenance.

Execute tests and static checks. Inspect the generated workbook's sheet list, record counts, sample cells and warnings programmatically. In your final Codex response, report which files were created, which commands were actually run, pass/fail counts, the successful June source substitution and any remaining QA blockers, the status of HS scope review, and steps to produce an official-ready report. Do not conceal unfinished steps. The supplemental June product-wise workbook needs to be in `./data/`; auto-discover it by structure even if its downloaded filename is opaque. Do not ask the user to rename the 16 original inputs. Do not stop after scaffolding; implement and exercise the complete pipeline.
