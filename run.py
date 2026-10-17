"""Run the loyalty and promotion ROI analysis end to end.

Colab:
    !git clone https://github.com/achux11/loyalty-promotion-roi.git
    %cd loyalty-promotion-roi
    !pip install -q kagglehub openpyxl
    !python run.py

Offline demo on synthetic data (no download):
    python run.py --synthetic
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loyalty_roi import campaigns, data, metrics, report, validate

OUT = Path("outputs")


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", help="folder with the Kaggle CSVs (default: download with kagglehub)")
    ap.add_argument("--synthetic", action="store_true", help="use the small synthetic dataset")
    ap.add_argument("--margin", type=float, default=0.30, help="assumed gross margin for ROI (default 0.30)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    d = data.synthetic() if args.synthetic else data.load(args.data_dir)
    checks = validate.checks(d)
    t = validate.clean(d["transactions"])

    kpis, ret, tier = metrics.member_kpis(t), metrics.retention(t), metrics.tiers(t)
    attach = metrics.attach_rate(t, d["products"])
    roi = campaigns.evaluate(t, d, margin=args.margin)
    s = campaigns.summary(roi)

    summary_rows = [
        ("Loyalty members (households)", t["household_key"].nunique()),
        ("Baskets (point-of-sale transactions)", t["basket_id"].nunique()),
        ("Line items analyzed", len(t)),
        ("Sales", round(t["sales_value"].sum(), 2)),
        ("Sales per member per 4-week period (median)", round(kpis["sales_per_member"].median(), 2)),
        ("Median period-to-period retention", round(ret["retention_rate"].median(), 4)),
        ("Top 25% of members: share of sales", round(tier["share_of_sales"].iloc[0], 4)),
        ("Campaigns evaluated", s["campaigns_evaluated"]),
        ("Campaigns with significant lift (p<0.05)", s["significant_lift"]),
        ("Campaigns with positive ROI", s["positive_roi"]),
        ("Incremental sales", round(s["incremental_sales"], 2)),
        ("Coupon cost", round(s["coupon_cost"], 2)),
        ("Portfolio payback (gross profit per $1 coupon cost)", round(s["portfolio_payback"], 2)),
        ("Assumed gross margin", args.margin),
        ("Rows flagged by validation", int(checks["rows_flagged"].sum())),
    ]
    report.excel_package(OUT / "loyalty_promotion_report.xlsx", summary_rows, roi, kpis, ret, tier, attach,
                         checks, s["by_type"])
    report.dashboard(roi, ret, tier, attach, OUT / "dashboard.png")
    (OUT / "post_mortem.md").write_text(campaigns.post_mortem(roi, s, args.margin))
    (OUT / "results.json").write_text(json.dumps({k: v for k, v in s.items() if k != "by_type"}, indent=2))

    print("\n===== RESULTS (paste this block back) =====")
    for k, v in summary_rows:
        print(f"{k}: {v:,}" if isinstance(v, (int, float)) and not isinstance(v, bool) else f"{k}: {v}")
    print("\nROI by campaign type:\n" + s["by_type"].to_string())
    print("\nAttach rate:\n" + attach.round(4).to_string())
    best = roi["roi"].idxmax()
    print(f"\nBest campaign: #{best} {roi.loc[best, 'type']} lift {roi.loc[best, 'lift_pct']:+.1%} "
          f"ROI {roi.loc[best, 'roi']:+.0%}")
    print("\nData validation:\n" + checks.to_string(index=False))
    print("===== END =====")
    return s


if __name__ == "__main__":
    main()
