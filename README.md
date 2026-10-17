# Loyalty & Promotion ROI Analysis

[![CI](https://github.com/achux11/loyalty-promotion-roi/actions/workflows/ci.yml/badge.svg)](https://github.com/achux11/loyalty-promotion-roi/actions/workflows/ci.yml)

**Did our promotions pay for themselves, and what do loyalty members spend?** This project answers both on
**dunnhumby's *The Complete Journey***: two years of point-of-sale transactions from ~2,500 loyalty-card
households at a food retailer, with the marketing campaigns and coupons they received.

It is built the way a marketing-finance team works: validate the data first, measure each promotion against a
control group with pre/post analysis, compute payback on coupon cost, and publish a monthly-style reporting
package in Excel plus a promotion post-mortem.

## What it measures
| Area | Output |
|---|---|
| **Promotion ROI** | For every campaign: pre/post difference-in-differences vs. untargeted members, incremental sales, coupon cost, incremental gross profit, **payback ratio and ROI**, p-value, redemption rate |
| **Loyalty members** | Active members, baskets and **sales per member (per-cap spend)** for each 4-week period; period-to-period **retention**; spend tiers (share of sales from the top 25% of members) |
| **Basket attach rate** | Share of snack baskets that also contain a soft drink, coupon baskets vs. non-coupon baskets (the grocery version of a combo promotion) |
| **Data validation** | Duplicates, missing keys, zero/negative sales, unknown products, redemptions outside campaign windows, targeted members with no purchases |

## How ROI is calculated
1. **Pre window** = the same number of days just before the campaign starts.
2. **Lift** = (targeted members' change in daily spend) − (untargeted members' change), so seasonality that hits everyone cancels out.
3. **Incremental sales** = lift × campaign days × targeted members.
4. **Cost** = coupon discounts targeted members received on that campaign's coupon products.
5. **Payback** = incremental gross profit ÷ cost, with gross margin as an explicit assumption (`--margin`, default 30%).

## Results
_Filled in after running on the full dataset (`python run.py`)._

## Outputs (`outputs/`)
- `loyalty_promotion_report.xlsx`: 8 tabs (Summary, Campaign ROI, ROI by Campaign Type, Member KPIs, Retention, Loyalty Tiers, Attach Rate, Data Validation)
- `post_mortem.md`: results, payback, best and worst campaign, lessons learned
- `dashboard.png`: one-page summary

## Run
**Google Colab (full data, ~5 minutes):**
```python
!git clone https://github.com/achux11/loyalty-promotion-roi.git
%cd loyalty-promotion-roi
!pip install -q kagglehub openpyxl
!python run.py
```
**Offline demo and tests (synthetic data with a planted campaign lift):**
```bash
pip install -r requirements.txt
python run.py --synthetic
pytest -q        # 7 tests
```

## Project structure
```
loyalty_roi/data.py       load the Kaggle tables, or build a synthetic copy for tests
loyalty_roi/validate.py   point-of-sale data checks and cleaning
loyalty_roi/metrics.py    per-cap spend, retention, spend tiers, attach rate
loyalty_roi/campaigns.py  pre/post difference-in-differences, payback, ROI, post-mortem
loyalty_roi/report.py     Excel reporting package and dashboard
run.py                    end-to-end run
tests/                    7 tests
```

## Limitations
- Campaign windows overlap, so a household can be in several campaigns at once; per-campaign lifts are estimates.
- Gross margin is assumed, not observed.
- Targeting was not random, so the control group is "similar members who were not targeted", not a true A/B test.

---
**Author:** Achintya Vamshi Nudurupati · [GitHub @achux11](https://github.com/achux11) · [LinkedIn](https://linkedin.com/in/achintya11)
Data: dunnhumby, *The Complete Journey* (via Kaggle).
