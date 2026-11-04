from datetime import date

import pandas as pd
import pytest

from riskdash.data.cache import CachedProvider
from riskdash.data.fixture_provider import FixtureProvider
from riskdash.data.provider import DataProviderError
from riskdash.engine import build_snapshot, excluded_warning
from riskdash.portfolio.models import Portfolio, Position

TODAY = date(2026, 10, 30)


def make_book(*extra: Position) -> Portfolio:
    return Portfolio(
        positions=[
            Position(ticker="AAA", quantity=1_000, avg_cost=90),
            Position(ticker="BBB", quantity=-500, avg_cost=110),
            *extra,
        ],
        cash=100_000,
    )


def test_snapshot_is_internally_consistent(provider):
    snap = build_snapshot(make_book(), provider, lookback=252, today=TODAY)
    v, pos = snap.valuation, snap.positions
    assert snap.n_obs == 252 and not snap.warnings
    assert v.nav == pytest.approx(100_000 + pos["market_value"].sum())
    assert snap.portfolio_beta == pytest.approx((pos["weight"] * pos["beta"]).sum())
    assert snap.dollar_beta == pytest.approx(snap.portfolio_beta * v.nav)
    assert snap.risk_contrib.sum() == pytest.approx(1.0)
    assert 0 < snap.portfolio_vol < 1


def test_blume_flag(provider):
    raw = build_snapshot(make_book(), provider, today=TODAY)
    adj = build_snapshot(make_book(), provider, blume=True, today=TODAY)
    assert adj.betas["AAA"] == pytest.approx(0.67 * raw.betas["AAA"] + 0.33)


def test_unknown_ticker_is_excluded_with_warning(provider):
    snap = build_snapshot(make_book(Position(ticker="NOPE", quantity=1)), provider, today=TODAY)
    assert snap.excluded == ["NOPE"]
    assert "NOPE" in snap.warnings[0]
    assert snap.warnings[0] == excluded_warning(snap.excluded)
    assert "NOPE" not in snap.positions.index


def test_holding_the_benchmark_itself(provider):
    snap = build_snapshot(make_book(Position(ticker="SPY", quantity=100)), provider, today=TODAY)
    assert snap.betas["SPY"] == pytest.approx(1.0)
    assert not snap.returns.columns.duplicated().any()


def test_short_history_warns(synthetic_prices):
    prices = synthetic_prices.copy()
    prices.loc[prices.index[:-150], "AAA"] = float("nan")  # AAA "listed" 150 days ago
    snap = build_snapshot(make_book(), FixtureProvider(prices), lookback=252, today=TODAY)
    assert snap.n_obs == 149
    assert "AAA" in snap.warnings[0]


def test_empty_portfolio_rejected(provider):
    with pytest.raises(ValueError, match="no positions"):
        build_snapshot(Portfolio(cash=1), provider, today=TODAY)


class FlakyProvider:
    def __init__(self, inner):
        self.inner, self.fail, self.calls = inner, False, 0

    def get_prices(self, tickers, start, end):
        self.calls += 1
        if self.fail:
            raise DataProviderError("down")
        return self.inner.get_prices(tickers, start, end)

    def get_meta(self, tickers):
        return self.inner.get_meta(tickers)


def test_cache_serves_fresh_then_stale_on_outage(provider, tmp_path):
    flaky = FlakyProvider(provider)
    cached = CachedProvider(flaky, cache_dir=tmp_path, price_ttl_s=3600)
    a = cached.get_prices(["AAA", "SPY"], date(2026, 1, 1), TODAY)
    b = cached.get_prices(["SPY", "AAA"], date(2026, 1, 1), TODAY)  # order-insensitive hit
    assert flaky.calls == 1
    pd.testing.assert_frame_equal(a, b, check_freq=False)

    cached.price_ttl_s = 0  # everything is now stale
    flaky.fail = True
    c = cached.get_prices(["AAA", "SPY"], date(2026, 6, 1), TODAY)
    assert cached.served_stale and c.index.min() >= pd.Timestamp("2026-06-01")


def test_cache_raises_when_no_fallback(provider, tmp_path):
    flaky = FlakyProvider(provider)
    flaky.fail = True
    with pytest.raises(DataProviderError):
        CachedProvider(flaky, cache_dir=tmp_path).get_prices(["AAA"], date(2026, 1, 1), TODAY)


def test_meta_cache(provider, tmp_path):
    cached = CachedProvider(provider, cache_dir=tmp_path)
    assert cached.get_meta(["AAA"])["AAA"].sector == "Technology"
    assert (
        CachedProvider(FixtureProvider(pd.DataFrame()), cache_dir=tmp_path)
        .get_meta(["AAA"])["AAA"]
        .name
        == "Alpha Inc"
    )
