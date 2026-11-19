# Limitations and review

- The configured HS8 list is a conservative analytical proposal, not an official Bangladesh power-sector definition. Human approval is required for official use.
- Generic static converters cannot be relabelled solar/grid inverters; automotive starter batteries are excluded; other battery chemistry/end-use remains ambiguous.
- General low-voltage wires, switches, relays, sockets and connectors can serve many industries and default to exclusion unless their description supports power-sector use.
- Several source HS8 descriptions are blank. The decision table marks parent-description fallbacks explicitly rather than inventing a commodity label.
- EPB cumulative figures can be revised. Negative monthly deltas are retained as net changes in successive cumulative reports and must not be described as negative shipments.
- Relevant hierarchy gaps are warnings. The May and October 2026 `8541` gaps illustrate why source grand totals alone do not prove complete selected-product detail.
- HS nomenclature or national tariff-line changes can break year-to-year comparability. Review code/description variants before extending the period.

Official-ready procedure: review all candidates; document decisions; mark every included row `approved`; rerun `validate`; resolve any critical in-scope issue; then run strict `report` without override flags.

