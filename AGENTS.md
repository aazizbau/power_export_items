# Project rules

- Preserve every workbook in `data/` byte-for-byte. Read them with `openpyxl` in read-only mode.
- Treat currency as integer USD cents after ingestion.
- Use the product-wise workbook's `8 Digit` sheet as June 2026 authority; use the truncated detailed June workbook only for QA.
- Never sum hierarchy levels or product subtotal and country detail rows together.
- Never clamp negative first differences. Retain, flag, and explain them.
- Strict publication requires 16 authoritative sources, no material in-scope blocker, and human-approved included HS8 decisions.
- Generated files belong under `outputs/` or `logs/` and are not committed.

