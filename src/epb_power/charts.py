from __future__ import annotations

import os
from datetime import datetime
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

    # A wide grouped chart keeps all five draft product groups comparable month by month.
    fig, axis = plt.subplots(figsize=(24, 10))
    positions = list(range(len(months)))
    width = 0.16
    colors = ["#1F4E78", "#70AD47", "#ED7D31", "#5B9BD5", "#A5A5A5"]
    for group_index, group in enumerate(groups):
        offset = (group_index - (len(groups) - 1) / 2) * width
        values = [lookup[(month, group)]["monthly_usd_million"] for month in months]
        bars = axis.bar(
            [position + offset for position in positions],
            [float("nan") if value is None else value for value in values],
            width=width,
            label=group,
            color=colors[group_index % len(colors)],
        )
        for bar, value in zip(bars, values, strict=True):
            if value is None:
                continue
            label = f"{value:.2f}M" if abs(value) >= 1 else f"{value * 1000:,.1f}K"
            axis.annotate(
                label,
                xy=(bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 3 if value >= 0 else -3),
                textcoords="offset points",
                ha="center",
                va="bottom" if value >= 0 else "top",
                rotation=90,
                fontsize=5.5,
                color="#222222",
            )
    axis.axhline(0, color="#444444", linewidth=0.8)
    axis.set_title("Monthly export value of five selected power-equipment product groups", fontsize=16)
    axis.set_ylabel("USD million (net change in FYTD cumulative reports)")
    axis.set_xticks(positions)
    axis.set_xticklabels(
        [
            datetime.strptime(month, "%Y-%m").strftime("%b %y")
            for month in months
        ],
        rotation=45,
        ha="right",
    )
    axis.grid(axis="y", alpha=0.25)
    axis.margins(y=0.18)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=5, fontsize=9)
    axis.text(
        0,
        -0.27,
        "Labels: M = USD million, K = USD thousand. Provisional draft HS scope; negative values are retained source revisions.",
        transform=axis.transAxes,
        fontsize=9,
        color="#666666",
    )
    fig.tight_layout()
    grouped_bars = output_dir / "monthly_five_product_grouped_bars.png"
    fig.savefig(grouped_bars, dpi=180, bbox_inches="tight")
    plt.close(fig)

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
    return [grouped_bars, trend, mom]

