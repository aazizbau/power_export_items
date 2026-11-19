from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def write_png_charts(monthly: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    cache_dir = output_dir / ".matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    groups = sorted({row["product_group"] for row in monthly})
    months = sorted({row["month"] for row in monthly})
    lookup = {(row["month"], row["product_group"]): row for row in monthly}
    fig, axis = plt.subplots(figsize=(13, 6.5))
    for group in groups:
        values = [lookup[(month, group)]["monthly_usd_million"] for month in months]
        axis.plot(months, values, marker="o", linewidth=1.8, label=group)
    axis.set_title("Selected power-equipment exports by product group")
    axis.set_ylabel("USD million (net change in FYTD cumulative reports)")
    axis.tick_params(axis="x", rotation=45)
    axis.grid(alpha=0.25)
    axis.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.tight_layout()
    trend = output_dir / "monthly_export_trend.png"
    fig.savefig(trend, dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(13, 6.5))
    for group in groups:
        values = [lookup[(month, group)]["mom_pct"] for month in months]
        axis.plot(months, values, marker="o", linewidth=1.4, label=group)
    axis.axhline(0, color="#444444", linewidth=0.8)
    axis.set_title("Month-on-month change by product group")
    axis.set_ylabel("Percent (NA where base is zero/missing)")
    axis.tick_params(axis="x", rotation=45)
    axis.grid(alpha=0.25)
    axis.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.tight_layout()
    mom = output_dir / "mom_growth.png"
    fig.savefig(mom, dpi=180)
    plt.close(fig)
    return [trend, mom]

