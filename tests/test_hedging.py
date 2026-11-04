import pandas as pd
import pytest

from riskdash.analytics.hedging import (
    ES_MULTIPLIER,
    MES_MULTIPLIER,
    hedged_beta,
    hedged_vol,
    hedged_weights,
    required_notional,
    size_hedge,
)
from riskdash.analytics.returns import daily_returns
from riskdash.analytics.volatility import annualized_cov, portfolio_vol

NAV = 10_000_000.0


def test_required_notional_hand_computed():
    # beta 0.60 -> 0: sell 0.60 * 10M = $6M of S&P exposure
    assert required_notional(0.0, 0.60, NAV) == pytest.approx(-6_000_000)
    # beta 0.60 -> 1.00: buy $4M
    assert required_notional(1.0, 0.60, NAV) == pytest.approx(4_000_000)


def test_long_beta_book_gets_short_hedge_and_vice_versa():
    assert required_notional(0.0, 0.8, NAV) < 0
    assert required_notional(0.5, -0.2, NAV) > 0
    assert required_notional(0.6, 0.6, NAV) == 0


def test_hedge_beta_scales_notional():
    assert required_notional(0.0, 0.6, NAV, hedge_beta=2.0) == pytest.approx(-3_000_000)


def test_spy_shares_exact_and_rounded():
    s = size_hedge(0.0, 0.60, NAV, unit_notional=500.0)  # SPY at $500
    assert s.exact_units == pytest.approx(-12_000)
    assert s.units == -12_000 and s.notional == pytest.approx(-6_000_000)
    assert s.residual_beta == pytest.approx(0.0, abs=1e-12)


def test_futures_unit_notional_and_rounding_residual():
    es_notional = 5_000 * ES_MULTIPLIER  # $250k per contract
    s = size_hedge(0.0, 0.59, NAV, es_notional)
    assert s.exact_units == pytest.approx(-23.6)
    assert s.units == -24
    assert s.post_beta == pytest.approx(0.59 - 24 * 250_000 / NAV)  # -0.01
    assert s.residual_beta == pytest.approx(-0.01)


def test_residual_never_exceeds_half_a_unit():
    for pb in (-0.4, 0.13, 0.59, 1.37):
        for unit in (500.0, 250_000.0, 25_000.0):
            s = size_hedge(0.25, pb, NAV, unit)
            assert abs(s.residual_beta) <= 0.5 * unit / NAV + 1e-12


def test_post_hedge_beta_reaches_target_when_units_are_fine():
    s = size_hedge(0.30, 0.95, NAV, 500.0)
    assert s.post_beta == pytest.approx(0.30, abs=500 / NAV)
    assert hedged_beta(0.95, NAV, s.notional) == pytest.approx(s.post_beta)


def test_target_equal_to_current_needs_no_trade():
    s = size_hedge(0.59, 0.59, NAV, 250_000.0)
    assert s.units == 0 and s.notional == 0 and s.residual_beta == pytest.approx(0)


def test_micro_contract_is_one_tenth_of_emini():
    assert ES_MULTIPLIER == 10 * MES_MULTIPLIER


def test_rounds_half_away_from_zero():
    assert size_hedge(0.0, 0.5, NAV, 10_000_000.0).units == -1  # exact -0.5
    assert size_hedge(1.0, 0.5, NAV, 10_000_000.0).units == 1  # exact +0.5


@pytest.mark.parametrize("nav", [0.0, -5.0])
def test_non_positive_nav_rejected(nav):
    with pytest.raises(ValueError):
        required_notional(0.0, 0.5, nav)


def test_non_positive_unit_notional_rejected():
    with pytest.raises(ValueError):
        size_hedge(0.0, 0.5, NAV, 0.0)


def test_hedged_weights_net_against_existing_spy_position():
    w = pd.Series({"AAA": 0.5, "SPY": 0.2})
    out = hedged_weights(w, notional=-3_000_000, nav=NAV)
    assert out["SPY"] == pytest.approx(-0.1) and out["AAA"] == 0.5


def test_hedged_vol_matches_unhedged_when_no_hedge(synthetic_prices):
    r = daily_returns(synthetic_prices)
    cov = annualized_cov(r)
    w = pd.Series({"AAA": 0.4, "BBB": 0.3})
    assert hedged_vol(w, 0.0, NAV, cov) == pytest.approx(portfolio_vol(w, cov))


def test_fully_hedging_a_spy_position_has_zero_vol(synthetic_prices):
    cov = annualized_cov(daily_returns(synthetic_prices))
    assert hedged_vol(pd.Series({"SPY": 1.0}), -NAV, NAV, cov) == pytest.approx(0, abs=1e-9)


def test_beta_hedge_reduces_vol_for_a_high_beta_book(synthetic_prices):
    from riskdash.analytics.beta import betas, portfolio_beta

    r = daily_returns(synthetic_prices)
    w = pd.Series({"AAA": 0.8})  # beta ~1.5 loading on SPY plus idiosyncratic noise
    pb = portfolio_beta(w, betas(r)[w.index])
    s = size_hedge(0.0, pb, NAV, 500.0)
    cov = annualized_cov(r)
    assert hedged_vol(w, s.notional, NAV, cov) < portfolio_vol(w, cov[w.index].loc[w.index])
