import numpy as np
import pandas as pd
import pytest

from riskdash.analytics.correlation import (
    average_pairwise_correlation,
    correlation_matrix,
    top_pairs,
)
from riskdash.analytics.exposure import UNCLASSIFIED, sector_exposure
from riskdash.analytics.returns import daily_returns


@pytest.fixture
def corr():
    return pd.DataFrame(
        [[1.0, 0.8, -0.2], [0.8, 1.0, 0.1], [-0.2, 0.1, 1.0]],
        index=list("ABC"),
        columns=list("ABC"),
    )


def test_correlation_matrix_properties(synthetic_prices):
    c = correlation_matrix(daily_returns(synthetic_prices))
    assert np.allclose(np.diag(c), 1.0)
    assert np.allclose(c, c.T)
    assert ((c >= -1) & (c <= 1)).all().all()
    # AAA and CCC both load on SPY, so they co-move; noise keeps it below 1
    assert 0.3 < c.loc["AAA", "CCC"] < 1


def test_average_pairwise_correlation(corr):
    assert average_pairwise_correlation(corr) == pytest.approx((0.8 - 0.2 + 0.1) / 3)


def test_average_pairwise_correlation_single_asset():
    assert np.isnan(average_pairwise_correlation(pd.DataFrame([[1.0]], index=["A"], columns=["A"])))


def test_top_pairs_sorted_without_duplicates(corr):
    pairs = top_pairs(corr, n=2)
    assert list(pairs.itertuples(index=False, name=None)) == [("A", "B", 0.8), ("B", "C", 0.1)]


@pytest.fixture
def book():
    weights = pd.Series({"AAPL": 0.10, "MSFT": 0.08, "TSLA": -0.04, "XOM": 0.05, "ZZZ": 0.02})
    sectors = {"AAPL": "Tech", "MSFT": "Tech", "TSLA": "Tech", "XOM": "Energy"}  # ZZZ unknown
    betas = pd.Series({"AAPL": 1.2, "MSFT": 1.0, "TSLA": 2.0, "XOM": 0.5, "ZZZ": 1.0})
    rc = pd.Series({"AAPL": 0.5, "MSFT": 0.4, "TSLA": -0.1, "XOM": 0.15, "ZZZ": 0.05})
    return weights, sector_exposure(weights, sectors, betas, rc)


def test_sector_long_short_net_gross(book):
    _, exp = book
    tech = exp.loc["Tech"]
    assert tech["long"] == pytest.approx(0.18)
    assert tech["short"] == pytest.approx(-0.04)
    assert tech["net"] == pytest.approx(0.14)
    assert tech["gross"] == pytest.approx(0.22)
    assert tech["positions"] == 3
    assert tech["beta_adj"] == pytest.approx(0.10 * 1.2 + 0.08 * 1.0 - 0.04 * 2.0)


def test_sector_totals_reconcile_to_portfolio(book):
    weights, exp = book
    assert exp["net"].sum() == pytest.approx(weights.sum())
    assert exp["gross"].sum() == pytest.approx(weights.abs().sum())
    assert exp["risk_contrib"].sum() == pytest.approx(1.0)
    assert (exp["long"] + exp["short"] - exp["net"]).abs().max() < 1e-12


def test_unknown_sector_and_ordering(book):
    _, exp = book
    assert exp.loc[UNCLASSIFIED, "net"] == pytest.approx(0.02)
    assert list(exp.index) == ["Tech", "Energy", UNCLASSIFIED]  # by gross, descending


def test_optional_columns_absent():
    exp = sector_exposure(pd.Series({"A": 0.5}), {"A": "Tech"})
    assert "beta_adj" not in exp and "risk_contrib" not in exp
