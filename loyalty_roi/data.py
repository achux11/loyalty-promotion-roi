"""Load dunnhumby's 'The Complete Journey' (Kaggle) or build a small synthetic copy for tests.

Every household in the dataset is a loyalty-card member, so each transaction line is a
point-of-sale record tied to a member.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

KAGGLE_DATASET = "frtgnn/dunnhumby-the-complete-journey"
FILES = {
    "transactions": ("transaction_data.csv", ["household_key", "basket_id", "day", "product_id", "quantity",
                                              "sales_value", "coupon_disc", "coupon_match_disc"]),
    "products": ("product.csv", None),
    "campaign_table": ("campaign_table.csv", None),
    "campaign_desc": ("campaign_desc.csv", None),
    "coupons": ("coupon.csv", None),
    "redemptions": ("coupon_redempt.csv", None),
}


def _find(root: str, name: str) -> str:
    hits = glob.glob(os.path.join(root, "**", name), recursive=True)
    if not hits:
        raise FileNotFoundError(f"{name} not found under {root}")
    return hits[0]


def load(root: str | None = None) -> dict[str, pd.DataFrame]:
    """Read the six tables used here. Column names are lower-cased so any Kaggle version works."""
    if root is None:
        import kagglehub
        root = kagglehub.dataset_download(KAGGLE_DATASET)
    out = {}
    for key, (fname, cols) in FILES.items():
        df = pd.read_csv(_find(root, fname), usecols=lambda c: cols is None or c.lower() in cols)
        df.columns = [c.lower() for c in df.columns]
        out[key] = df
    return out


COMMODITIES = ["BAG SNACKS", "SOFT DRINKS", "FLUID MILK PRODUCTS", "BAKED BREAD/BUNS/ROLLS", "CHEESE", "FROZEN PIZZA"]


def synthetic(seed: int = 7, lift: float = 1.25, n_households: int = 300, n_days: int = 336) -> dict[str, pd.DataFrame]:
    """Same schema as the real data, with a known campaign lift and a few planted data problems."""
    rng = np.random.default_rng(seed)
    products = pd.DataFrame({
        "product_id": np.arange(1000, 1060),
        "commodity_desc": [COMMODITIES[i % len(COMMODITIES)] for i in range(60)],
        "department": "GROCERY",
    })
    price = dict(zip(products.product_id, rng.uniform(1, 8, 60).round(2)))
    campaigns = pd.DataFrame({"campaign": [1, 2, 3], "description": ["TypeA", "TypeB", "TypeC"],
                              "start_day": [120, 200, 280], "end_day": [160, 240, 310]})
    hh = np.arange(1, n_households + 1)
    treated = {c: set(rng.choice(hh, size=n_households * 2 // 5, replace=False)) for c in campaigns.campaign}
    camp_products = {c: set(rng.choice(products.product_id, size=8, replace=False)) for c in campaigns.campaign}
    base_p = rng.uniform(0.08, 0.25, n_households)

    rows, reds, basket = [], [], 0
    for d in range(1, n_days + 1):
        active = [c for c in campaigns.itertuples() if c.start_day <= d <= c.end_day]
        for i, h in enumerate(hh):
            in_camp = [c.campaign for c in active if h in treated[c.campaign]]
            p = base_p[i] * (lift if in_camp else 1.0)
            if rng.random() >= p:
                continue
            basket += 1
            items = rng.choice(products.product_id, size=rng.integers(1, 7), replace=False)
            if 1000 in items or rng.random() < 0.3:          # snacks often bought with a drink
                items = np.union1d(items, [1001])
            for pid in items:
                q = int(rng.integers(1, 3))
                cdisc = 0.0
                if in_camp and any(pid in camp_products[c] for c in in_camp) and rng.random() < 0.3:
                    cdisc = -0.5
                    reds.append({"household_key": h, "day": d, "coupon_upc": int(pid) * 10, "campaign": in_camp[0]})
                rows.append({"household_key": h, "basket_id": basket, "day": d, "product_id": int(pid),
                             "quantity": q, "sales_value": round(price[pid] * q, 2),
                             "coupon_disc": cdisc, "coupon_match_disc": 0.0})
    t = pd.DataFrame(rows)
    # planted data problems for the validation step
    t = pd.concat([t, t.head(5)], ignore_index=True)                                   # 5 duplicates
    t.loc[t.index[10:13], "sales_value"] = 0.0                                           # 3 zero-sales lines
    t.loc[t.index[20:22], "product_id"] = 99999                                          # 2 unknown products
    campaign_table = pd.DataFrame([{"description": campaigns.description[c - 1], "household_key": h, "campaign": c}
                                   for c in campaigns.campaign for h in treated[c]])
    coupons = pd.DataFrame([{"coupon_upc": int(p) * 10, "product_id": int(p), "campaign": c}
                            for c in campaigns.campaign for p in camp_products[c]])
    return {"transactions": t, "products": products, "campaign_table": campaign_table,
            "campaign_desc": campaigns, "coupons": coupons, "redemptions": pd.DataFrame(reds)}
