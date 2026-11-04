import io

import pytest
from pydantic import ValidationError

from riskdash.portfolio.io import (
    PortfolioImportError,
    portfolio_to_csv,
    read_portfolio_csv,
)
from riskdash.portfolio.models import Portfolio, Position


def test_ticker_is_normalized():
    assert Position(ticker=" brk.b ", quantity=1).ticker == "BRK.B"


@pytest.mark.parametrize("ticker", ["", "CASH", "BAD TICKER", "TOOLONGTICKER1"])
def test_bad_tickers_rejected(ticker):
    with pytest.raises(ValidationError):
        Position(ticker=ticker, quantity=1)


def test_zero_quantity_rejected():
    with pytest.raises(ValidationError):
        Position(ticker="AAPL", quantity=0)


def test_duplicate_tickers_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        Portfolio(
            positions=[Position(ticker="AAPL", quantity=1), Position(ticker="aapl", quantity=2)]
        )


def test_csv_round_trip_preserves_shorts_and_cash():
    pf = Portfolio(
        positions=[
            Position(ticker="AAPL", quantity=100, avg_cost=150.0, sector="Technology"),
            Position(ticker="TSLA", quantity=-50, avg_cost=250.0),
            Position(ticker="XOM", quantity=10),
        ],
        cash=12_345.67,
    )
    assert read_portfolio_csv(io.StringIO(portfolio_to_csv(pf))) == pf


def test_csv_errors_are_reported_per_row():
    csv = "ticker,quantity,avg_cost\nAAPL,abc,1\nMSFT,0,1\nGOOG,5,-3\n,,\nNVDA,1,100\n"
    with pytest.raises(PortfolioImportError) as exc:
        read_portfolio_csv(io.StringIO(csv))
    errs = exc.value.errors
    assert len(errs) == 3
    assert errs[0].startswith("row 2") and "not a number" in errs[0]
    assert errs[1].startswith("row 3 (MSFT)")
    assert errs[2].startswith("row 4 (GOOG)")


def test_csv_missing_columns():
    with pytest.raises(PortfolioImportError, match="quantity"):
        read_portfolio_csv(io.StringIO("ticker\nAAPL\n"))


def test_csv_headers_case_insensitive_and_cash_summed():
    pf = read_portfolio_csv(io.StringIO("Ticker,Quantity\nAAPL,1\nCASH,100\ncash,50\n"))
    assert pf.cash == 150 and pf.tickers == ["AAPL"]


@pytest.mark.parametrize("qty", ["", "nan", "inf", "-inf"])
def test_csv_non_finite_quantity_rejected(qty):
    with pytest.raises(PortfolioImportError, match="row 2.*not a number"):
        read_portfolio_csv(io.StringIO(f"ticker,quantity\nAAPL,{qty}\n"))


@pytest.mark.parametrize("qty", ["", "nan", "inf"])
def test_csv_non_finite_cash_rejected(qty):
    with pytest.raises(PortfolioImportError, match="row 3.*not a number"):
        read_portfolio_csv(io.StringIO(f"ticker,quantity\nAAPL,1\nCASH,{qty}\n"))


def test_model_rejects_non_finite_values():
    with pytest.raises(ValidationError):
        Position(ticker="AAPL", quantity=float("nan"))
    with pytest.raises(ValidationError):
        Portfolio(cash=float("inf"))
