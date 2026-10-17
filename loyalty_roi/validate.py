"""Validate point-of-sale and campaign data before anything is reported."""
from __future__ import annotations

import pandas as pd

KEYS = ["household_key", "basket_id", "product_id"]


def checks(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    t = d["transactions"]
    r = d["redemptions"].merge(d["campaign_desc"][["campaign", "start_day", "end_day"]], on="campaign", how="left")
    rows = [
        ("Missing household, basket or product key", t[KEYS].isna().any(axis=1).sum(), "excluded"),
        ("Exact duplicate line items", t.duplicated().sum(), "excluded"),
        ("Zero or negative sales value", (t["sales_value"] <= 0).sum(), "excluded from spend"),
        ("Zero-quantity lines", (t["quantity"] <= 0).sum(), "flagged"),
        ("Products missing from product master", (~t["product_id"].isin(d["products"]["product_id"])).sum(),
         "kept as UNKNOWN category"),
        ("Coupon redemptions outside the campaign window",
         ((r["day"] < r["start_day"]) | (r["day"] > r["end_day"])).sum(), "flagged"),
        ("Targeted households with no purchases",
         (~d["campaign_table"]["household_key"].isin(t["household_key"])).sum(), "flagged"),
    ]
    return pd.DataFrame(rows, columns=["check", "rows_flagged", "action"]).astype({"rows_flagged": int})


def clean(t: pd.DataFrame) -> pd.DataFrame:
    t = t.dropna(subset=KEYS).drop_duplicates()
    return t[t["sales_value"] > 0].copy()
