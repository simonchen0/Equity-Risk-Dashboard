import pandas as pd
import pytest

from riskdash.portfolio.models import Portfolio, Position
from riskdash.portfolio.valuation import value_portfolio


@pytest.fixture
def book():
    # Long 100 AAA @ cost 80, short 50 BBB @ cost 220, 10,000 cash.
    pf = Portfolio(
        positions=[
            Position(ticker="AAA", quantity=100, avg_cost=80),
            Position(ticker="BBB", quantity=-50, avg_cost=220),
        ],
        cash=10_000,
    )
    last = pd.Series({"AAA": 100.0, "BBB": 200.0})
    prev = pd.Series({"AAA": 98.0, "BBB": 204.0})
    return value_portfolio(pf, last, prev)


def test_market_values_and_nav(book):
    pos = book.positions
    assert pos.loc["AAA", "market_value"] == 10_000
    assert pos.loc["BBB", "market_value"] == -10_000
    assert book.nav == 10_000  # 10k cash + 10k long - 10k short
    assert book.long_mv == 10_000 and book.short_mv == -10_000


def test_weights_and_exposures(book):
    assert book.weights.to_dict() == {"AAA": 1.0, "BBB": -1.0}
    assert book.gross_exposure == pytest.approx(2.0)
    assert book.net_exposure == pytest.approx(0.0)


def test_pnl_signs(book):
    pos = book.positions
    assert pos.loc["AAA", "unrealized_pnl"] == 2_000  # (100-80)*100
    assert pos.loc["BBB", "unrealized_pnl"] == 1_000  # (200-220)*-50: short gains on a fall
    assert pos.loc["AAA", "unrealized_pnl_pct"] == pytest.approx(0.25)
    assert pos.loc["BBB", "unrealized_pnl_pct"] == pytest.approx(20 / 220)
    assert pos.loc["AAA", "day_pnl"] == 200
    assert pos.loc["BBB", "day_pnl"] == 200  # (200-204)*-50
    assert book.day_pnl == 400
    assert book.prev_nav == 10_000 + 9_800 - 10_200
    assert book.day_return == pytest.approx(400 / 9_600)


def test_missing_cost_basis_is_excluded_from_unrealized():
    pf = Portfolio(positions=[Position(ticker="AAA", quantity=1)], cash=0)
    v = value_portfolio(pf, pd.Series({"AAA": 10.0}), pd.Series({"AAA": 9.0}))
    assert v.unrealized_pnl == 0 and v.day_pnl == 1


def test_missing_price_raises():
    pf = Portfolio(positions=[Position(ticker="AAA", quantity=1)])
    with pytest.raises(ValueError, match="AAA"):
        value_portfolio(pf, pd.Series(dtype=float), pd.Series(dtype=float))


def test_non_positive_nav_raises():
    pf = Portfolio(positions=[Position(ticker="AAA", quantity=-1)], cash=0)
    with pytest.raises(ValueError, match="NAV"):
        value_portfolio(pf, pd.Series({"AAA": 10.0}), pd.Series({"AAA": 10.0}))
