"""Promotion ROI: pre/post difference-in-differences for each campaign, with payback on coupon cost."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def evaluate(t: pd.DataFrame, d: dict[str, pd.DataFrame], margin: float = 0.30) -> pd.DataFrame:
    """For each campaign, compare targeted members with untargeted members, before vs. during.

    Pre window = the same number of days immediately before the campaign starts.
    Incremental sales = (targeted change in daily spend - control change) x days x targeted members.
    Cost = coupon discounts that targeted members received on the campaign's coupon products.
    Incremental gross profit uses an assumed gross margin (default 30%).
    """
    first_day = t.groupby("household_key")["day"].min()
    rows = []
    for c in d["campaign_desc"].itertuples():
        length = c.end_day - c.start_day + 1
        pre_start = c.start_day - length
        if pre_start < t["day"].min():
            continue
        eligible = first_day[first_day < pre_start].index
        targeted = set(d["campaign_table"].loc[d["campaign_table"]["campaign"] == c.campaign, "household_key"])
        is_t = eligible.isin(list(targeted))
        if is_t.sum() < 10 or (~is_t).sum() < 10:
            continue

        def spend(lo, hi):
            w = t[(t["day"] >= lo) & (t["day"] <= hi)]
            return w.groupby("household_key")["sales_value"].sum().reindex(eligible, fill_value=0.0) / length

        pre, dur = spend(pre_start, c.start_day - 1), spend(c.start_day, c.end_day)
        change = dur - pre
        did = change[is_t].mean() - change[~is_t].mean()
        p_value = stats.ttest_ind(change[is_t], change[~is_t], equal_var=False).pvalue
        n_t = int(is_t.sum())
        incr_sales = did * length * n_t

        window = t[(t["day"] >= c.start_day) & (t["day"] <= c.end_day)]
        prods = set(d["coupons"].loc[d["coupons"]["campaign"] == c.campaign, "product_id"])
        mask = window["household_key"].isin(targeted) & window["product_id"].isin(prods)
        cost = float(-(window.loc[mask, "coupon_disc"] + window.loc[mask, "coupon_match_disc"]).sum())
        red = d["redemptions"][d["redemptions"]["campaign"] == c.campaign]
        incr_gp = incr_sales * margin
        rows.append({
            "campaign": c.campaign, "type": c.description, "start_day": c.start_day, "end_day": c.end_day,
            "days": length, "targeted_members": n_t, "control_members": int((~is_t).sum()),
            "pre_spend_per_day_targeted": pre[is_t].mean(), "during_spend_per_day_targeted": dur[is_t].mean(),
            "lift_per_member_day": did, "lift_pct": did / pre[is_t].mean() if pre[is_t].mean() else np.nan,
            "p_value": p_value, "incremental_sales": incr_sales, "coupon_cost": cost,
            "incremental_gross_profit": incr_gp,
            "payback_ratio": incr_gp / cost if cost > 0 else np.nan,
            "roi": (incr_gp - cost) / cost if cost > 0 else np.nan,
            "redeeming_members": red["household_key"].nunique(),
            "redemption_rate": red["household_key"].nunique() / n_t,
        })
    return pd.DataFrame(rows).set_index("campaign")


def summary(roi: pd.DataFrame) -> dict:
    sig = roi[roi["p_value"] < 0.05]
    cost, gp = roi["coupon_cost"].sum(), roi["incremental_gross_profit"].sum()
    return {
        "campaigns_evaluated": len(roi),
        "significant_lift": int((sig["lift_per_member_day"] > 0).sum()),
        "positive_roi": int((roi["roi"] > 0).sum()),
        "incremental_sales": float(roi["incremental_sales"].sum()),
        "coupon_cost": float(cost),
        "incremental_gross_profit": float(gp),
        "portfolio_payback": float(gp / cost) if cost > 0 else float("nan"),
        "by_type": roi.groupby("type").agg(campaigns=("roi", "size"), median_lift_pct=("lift_pct", "median"),
                                           median_roi=("roi", "median"),
                                           redemption_rate=("redemption_rate", "median")).round(3),
    }


def post_mortem(roi: pd.DataFrame, s: dict, margin: float) -> str:
    best = roi["roi"].idxmax()
    worst = roi["roi"].idxmin()
    b, w = roi.loc[best], roi.loc[worst]
    lines = [
        "# Promotion post-mortem",
        "",
        f"**Scope:** {s['campaigns_evaluated']} campaigns, pre/post vs. untargeted members, "
        f"gross margin assumed at {margin:.0%}.",
        "",
        "## Results",
        f"- Incremental sales: ${s['incremental_sales']:,.0f} for ${s['coupon_cost']:,.0f} of coupon cost.",
        f"- Portfolio payback: {s['portfolio_payback']:.1f}x gross profit per $1 of coupon cost.",
        f"- {s['significant_lift']} of {s['campaigns_evaluated']} campaigns showed a statistically significant "
        f"lift (p < 0.05); {s['positive_roi']} returned more gross profit than they cost.",
        "",
        "## Best and worst",
        f"- Best: campaign {best} ({b['type']}), lift {b['lift_pct']:+.1%}, ROI {b['roi']:+.0%}, "
        f"redemption rate {b['redemption_rate']:.1%}.",
        f"- Worst: campaign {worst} ({w['type']}), lift {w['lift_pct']:+.1%}, ROI {w['roi']:+.0%}, "
        f"redemption rate {w['redemption_rate']:.1%}.",
        "",
        "## Lessons learned",
        "- Judge a promotion on incremental spend against a control group, not on redemptions alone.",
        "- Campaign windows overlap, so a member can be in several at once; treat single-campaign lifts as estimates.",
        "- Margin is an assumption: rerun with `--margin` to see how payback changes.",
    ]
    return "\n".join(lines) + "\n"
