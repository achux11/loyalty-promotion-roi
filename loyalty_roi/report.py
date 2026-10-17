"""Monthly-style reporting package (Excel) and a one-page dashboard image."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SURFACE, INK, INK_2, GRID, BLUE, GREY = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6", "#b7b5ae"


def excel_package(path: Path, summary_rows: list, roi, kpis, ret, tier, attach, checks, by_type) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame(summary_rows, columns=["Metric", "Value"]).to_excel(xw, sheet_name="Summary", index=False)
        roi.round(4).to_excel(xw, sheet_name="Campaign ROI")
        by_type.to_excel(xw, sheet_name="ROI by Campaign Type")
        kpis.to_excel(xw, sheet_name="Member KPIs (4-week)")
        ret.round(4).to_excel(xw, sheet_name="Retention")
        tier.to_excel(xw, sheet_name="Loyalty Tiers")
        attach.round(4).to_excel(xw, sheet_name="Attach Rate")
        checks.to_excel(xw, sheet_name="Data Validation", index=False)
        for ws in xw.book.worksheets:
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 48)
            ws.freeze_panes = "B2"


def _style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=10)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.set_axisbelow(True)


def dashboard(roi, ret, tier, attach, path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), facecolor=SURFACE)
    fig.suptitle("Loyalty members and promotion ROI (dunnhumby, The Complete Journey)",
                 x=0.06, ha="left", fontsize=14, fontweight="bold", color=INK)

    ax = axes[0, 0]
    r = roi["roi"].dropna().sort_values() * 100
    ax.barh([f"#{i}" for i in r.index], r.values, color=[BLUE if v > 0 else GREY for v in r.values], height=0.6)
    ax.axvline(0, color=INK_2, linewidth=0.8)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", labelsize=7)
    _style(ax, "ROI by campaign (%), blue = paid back")

    ax = axes[0, 1]
    ax.plot(ret.index, ret["retention_rate"] * 100, color=BLUE, linewidth=2, marker="o", markersize=3)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_xlabel("4-week period", color=INK_2, fontsize=9)
    _style(ax, "Member retention, period to next period (%)")

    ax = axes[1, 0]
    ax.bar(tier.index.astype(str), tier["share_of_sales"] * 100, color=BLUE, width=0.55)
    for i, v in enumerate(tier["share_of_sales"] * 100):
        ax.text(i, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9, color=INK)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    _style(ax, "Share of sales by member spend tier (%)")

    ax = axes[1, 1]
    a = attach.drop(index="All anchor baskets", errors="ignore")["attach_rate"] * 100
    ax.bar(a.index.astype(str), a.values, color=[BLUE if "Coupon" in str(i) else GREY for i in a.index], width=0.5)
    for i, v in enumerate(a.values):
        ax.text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=9, color=INK)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    _style(ax, f"{attach['attach'].iloc[0].title()} attach rate in {attach['anchor'].iloc[0].title()} baskets (%)")

    fig.tight_layout(rect=(0.03, 0, 1, 0.95))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
