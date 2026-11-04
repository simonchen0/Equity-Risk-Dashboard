import numpy as np
import pandas as pd
import pytest

from riskdash.analytics.beta import betas, blume_adjust, dollar_beta, portfolio_beta, r_squared
from riskdash.analytics.returns import aligned_window, daily_returns
from riskdash.analytics.volatility import (
    annualized_cov,
    annualized_vol,
    portfolio_vol,
    risk_contributions,
)


def test_daily_returns_are_simple_returns():
    prices = pd.DataFrame(
        {"A": [100.0, 110.0, 99.0]}, index=pd.bdate_range("2026-01-01", periods=3)
    )
    r = daily_returns(prices)
    assert r["A"].tolist() == pytest.approx([0.10, -0.10])


def test_aligned_window_drops_incomplete_dates_and_trims():
    idx = pd.bdate_range("2026-01-01", periods=5)
    r = pd.DataFrame({"A": [0.1, 0.2, 0.3, 0.4, 0.5], "B": [np.nan, 1, 2, 3, 4]}, index=idx)
    w = aligned_window(r, lookback=3)
    assert list(w.index) == list(idx[2:]) and w.notna().all().all()


def test_beta_recovers_synthetic_loading(synthetic_prices):
    r = daily_returns(synthetic_prices)
    b = betas(r)
    assert b["SPY"] == pytest.approx(1.0)
    assert b["AAA"] == pytest.approx(1.5, abs=0.1)
    assert b["BBB"] == pytest.approx(0.5, abs=0.1)
    # identical to an OLS fit
    slope = np.polyfit(r["SPY"], r["AAA"], 1)[0]
    assert b["AAA"] == pytest.approx(slope)


def test_r_squared_bounds(synthetic_prices):
    r2 = r_squared(daily_returns(synthetic_prices))
    assert r2["SPY"] == pytest.approx(1.0)
    assert ((r2 >= 0) & (r2 <= 1)).all()


def test_blume_adjust():
    assert blume_adjust(1.0) == pytest.approx(1.0)
    assert blume_adjust(2.0) == pytest.approx(1.67)
    assert blume_adjust(0.0) == pytest.approx(0.33)


def test_portfolio_and_dollar_beta_with_cash_and_shorts():
    b = pd.Series({"A": 1.5, "B": 0.8})
    # 60% A long, 20% B short, remaining NAV in cash -> 0.6*1.5 - 0.2*0.8
    assert portfolio_beta(pd.Series({"A": 0.6, "B": -0.2}), b) == pytest.approx(0.74)
    assert dollar_beta(pd.Series({"A": 600.0, "B": -200.0}), b) == pytest.approx(740.0)


def test_portfolio_beta_missing_beta_is_nan_not_zero():
    assert np.isnan(portfolio_beta(pd.Series({"A": 0.5, "B": 0.5}), pd.Series({"A": 1.0})))


def test_two_asset_vol_closed_form():
    s1, s2, rho, w1, w2 = 0.20, 0.30, 0.25, 0.6, 0.4
    cov = pd.DataFrame(
        [[s1**2, rho * s1 * s2], [rho * s1 * s2, s2**2]], index=["A", "B"], columns=["A", "B"]
    )
    w = pd.Series({"A": w1, "B": w2})
    expected = np.sqrt(w1**2 * s1**2 + w2**2 * s2**2 + 2 * w1 * w2 * rho * s1 * s2)
    assert portfolio_vol(w, cov) == pytest.approx(expected)
    rc = risk_contributions(w, cov)
    assert rc.sum() == pytest.approx(1.0)
    assert rc["A"] == pytest.approx(w1 * (w1 * s1**2 + w2 * rho * s1 * s2) / expected**2)


def test_hedge_short_has_negative_risk_contribution():
    cov = pd.DataFrame([[0.04, 0.036], [0.036, 0.04]], index=["A", "B"], columns=["A", "B"])
    rc = risk_contributions(pd.Series({"A": 1.0, "B": -0.5}), cov)
    assert rc["B"] < 0 and rc.sum() == pytest.approx(1.0)


def test_annualization(synthetic_prices):
    r = daily_returns(synthetic_prices)
    assert annualized_vol(r)["SPY"] == pytest.approx(r["SPY"].std() * np.sqrt(252))
    assert annualized_cov(r).loc["SPY", "SPY"] == pytest.approx(annualized_vol(r)["SPY"] ** 2)
