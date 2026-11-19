from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

EXPECTED_MONTHS = tuple(
    [f"2025-{m:02d}" for m in range(7, 13)]
    + [f"2026-{m:02d}" for m in range(1, 11)]
)


@dataclass(frozen=True)
class CommodityRow:
    period: str
    code: str
    level: int
    description: str
    raw_description: str
    cents: int
    source_file: str
    source_row: int
    report_format: str


@dataclass
class WorkbookInfo:
    path: Path
    filename: str
    sha256: str
    modified_at: str
    report_format: str = "unrecognized"
    period_text: str = ""
    period: str | None = None
    header_valid: bool = False
    rows: list[CommodityRow] = field(default_factory=list)
    country_rows: int = 0
    reported_total_cents: int | None = None
    counts: dict[int, int] = field(default_factory=dict)
    chapters: set[str] = field(default_factory=set)
    selected: bool = False
    selection_reason: str = "not_evaluated"
    parse_errors: list[str] = field(default_factory=list)

    @property
    def hs8(self) -> dict[str, CommodityRow]:
        return {row.code: row for row in self.rows if row.level == 8}

