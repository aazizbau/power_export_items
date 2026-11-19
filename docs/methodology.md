# Methodology

## Source recognition and precedence

Workbooks are identified from sheet names and header cells, then mapped from A3 period text. Fifteen periods use `Worksheet 1` detailed reports. June 2026 uses only product subtotal rows from the Product-wise Export (Goods) `8 Digit` sheet: an eight-digit code in column A, blank country column B, and USD in column C. Country rows are counted for QA but never added to subtotals.

All source amounts are normalized with `Decimal` to integer cents. Hierarchical HS2/HS4/HS6 values are retained for QA and never added to HS8 values. SHA-256 checksums identify every source.

## Calculation

The panel is the union of included HS8 codes. Before a code's first positive observation within a fiscal year, absence is recorded as `no_export_evidence` and a zero cumulative amount. Once positive, disappearance invalidates the observation rather than creating a zero. July monthly value equals July FYTD; later months are cents-safe first differences. Product groups are aggregated only after HS8 calculations.

MoM percentage is calculated only when both monthly values exist and the prior value is positive. Zero and missing bases remain NA. Category share is calculated only when the full included sector total exists.

## QA gates

Strict publication requires all 16 authoritative months, a usable June product-wise source with Chapters 85/90, cent-tolerant agreement on the June overlap, no material included-code disappearance, and approved scope decisions. Negative deltas are warnings retained in the data. Relevant HS4/HS6 subtotal-to-HS8 gaps are surfaced without asserting that unrelated national gaps invalidate the selected scope.

