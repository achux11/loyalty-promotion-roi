"""Loyalty member KPIs: per-cap spend, retention, member tiers and basket attach rate."""
from __future__ import annotations

import pandas as pd

PERIOD_DAYS = 28   # 4-week reporting periods


def with_period(t: pd.DataFrame) -> pd.DataFrame:
    return t.assign(period=(t["day"] - 1) // PERIOD_DAYS + 1)


def member_kpis(t: pd.DataFrame) -> pd.DataFrame:
    """One row per 4-week period: active members, baskets, sales and per-cap spend."""
    t = with_period(t)
    g = t.groupby("period").agg(active_members=("household_key", "nunique"),
                                baskets=("basket_id", "nunique"), sales=("sales_value", "sum"))
    g["sales_per_member"] = g["sales"] / g["active_members"]
    g["baskets_per_member"] = g["baskets"] / g["active_members"]
    g["avg_basket"] = g["sales"] / g["baskets"]
    return g.round(2)


def retention(t: pd.DataFrame) -> pd.DataFrame:
    """Share of members active in one 4-week period who are active again in the next."""
    t = with_period(t)
    sets = t.groupby("period")["household_key"].apply(set)
    rows = [{"period": p, "active_members": len(sets[p]),
             "retained_next_period": len(sets[p] & sets[p + 1]),
             "retention_rate": len(sets[p] & sets[p + 1]) / len(sets[p])}
            for p in sets.index if p + 1 in sets.index]
    return pd.DataFrame(rows).set_index("period")


def tiers(t: pd.DataFrame) -> pd.DataFrame:
    """Members split into spend quartiles: share of sales and per-cap spend by tier."""
    spend = t.groupby("household_key")["sales_value"].sum()
    q = pd.qcut(spend.rank(method="first"), 4, labels=["Bottom 25%", "Lower-mid 25%", "Upper-mid 25%", "Top 25%"])
    g = spend.groupby(q, observed=True).agg(members="count", sales="sum")
    g["share_of_sales"] = g["sales"] / g["sales"].sum()
    g["sales_per_member"] = g["sales"] / g["members"]
    return g.iloc[::-1].round(3)


def attach_rate(t: pd.DataFrame, products: pd.DataFrame, anchor: str = "BAG SNACKS",
                attach: str = "SOFT DRINKS") -> pd.DataFrame:
    """Of baskets containing the anchor category, the share that also contain the attach category,
    split by whether the basket used a coupon (a stand-in for a combo promotion)."""
    cat = t.merge(products[["product_id", "commodity_desc"]], on="product_id", how="left")
    cat["commodity_desc"] = cat["commodity_desc"].fillna("UNKNOWN")
    flags = pd.DataFrame({"basket_id": cat["basket_id"],
                          "has_anchor": cat["commodity_desc"].eq(anchor),
                          "has_attach": cat["commodity_desc"].eq(attach),
                          "used_coupon": cat["coupon_disc"].lt(0)})
    b = flags.groupby("basket_id").max()
    b = b[b["has_anchor"]]
    out = b.groupby("used_coupon")["has_attach"].agg(baskets="count", attach_rate="mean")
    out.index = out.index.map({True: "Coupon basket", False: "No coupon"})
    out.loc["All anchor baskets"] = [len(b), b["has_attach"].mean()]
    out["anchor"], out["attach"] = anchor, attach
    return out
