import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from loyalty_roi import campaigns, data, metrics, report, validate


@pytest.fixture(scope="module")
def d():
    return data.synthetic()


@pytest.fixture(scope="module")
def t(d):
    return validate.clean(d["transactions"])


def test_validation_catches_planted_problems(d):
    c = validate.checks(d).set_index("check")["rows_flagged"]
    assert c["Exact duplicate line items"] >= 5
    assert c["Zero or negative sales value"] >= 3
    assert c["Products missing from product master"] >= 2


def test_clean_removes_duplicates_and_zero_sales(d, t):
    assert not t.duplicated().any() and (t["sales_value"] > 0).all()
    assert len(t) < len(d["transactions"])


def test_campaigns_recover_planted_lift(d, t):
    roi = campaigns.evaluate(t, d)
    assert len(roi) == 3
    assert (roi["lift_pct"] > 0.05).all()          # planted lift is +25% visit rate
    assert (roi["p_value"] < 0.05).sum() >= 2      # the shortest campaign has the least data
    assert (roi["coupon_cost"] > 0).all() and (roi["incremental_sales"] > 0).all()


def test_no_lift_means_no_significant_effect():
    d0 = data.synthetic(lift=1.0, seed=11)
    roi = campaigns.evaluate(validate.clean(d0["transactions"]), d0)
    assert (roi["lift_pct"].abs() < 0.10).all()
    assert (roi["p_value"] < 0.05).sum() <= 1


def test_member_metrics_are_sane(t):
    k, r, tier = metrics.member_kpis(t), metrics.retention(t), metrics.tiers(t)
    assert (k["sales_per_member"] > 0).all()
    assert r["retention_rate"].between(0, 1).all()
    assert abs(tier["share_of_sales"].sum() - 1) < 0.01
    assert tier["share_of_sales"].iloc[0] > tier["share_of_sales"].iloc[-1]


def test_attach_rate_between_zero_and_one(d, t):
    a = metrics.attach_rate(t, d["products"])
    assert a["attach_rate"].between(0, 1).all()
    assert "All anchor baskets" in a.index


def test_report_package_has_all_sheets(d, t, tmp_path):
    roi = campaigns.evaluate(t, d)
    s = campaigns.summary(roi)
    a = metrics.attach_rate(t, d["products"])
    path = tmp_path / "r.xlsx"
    report.excel_package(path, [("x", 1)], roi, metrics.member_kpis(t), metrics.retention(t),
                         metrics.tiers(t), a, validate.checks(d), s["by_type"])
    sheets = pd.ExcelFile(path).sheet_names
    assert sheets == ["Summary", "Campaign ROI", "ROI by Campaign Type", "Member KPIs (4-week)", "Retention",
                      "Loyalty Tiers", "Attach Rate", "Data Validation"]
    report.dashboard(roi, metrics.retention(t), metrics.tiers(t), a, tmp_path / "d.png")
    assert (tmp_path / "d.png").stat().st_size > 10_000
