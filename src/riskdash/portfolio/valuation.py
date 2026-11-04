"""Mark-to-market valuation: market value, NAV, weights, exposures, P&L."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from riskdash.portfolio.models import Portfolio


@dataclass(frozen=True)
class Valuation:
    positions: pd.DataFrame  # one row per position, indexed by ticker
    cash: float
    nav: float
    prev_nav: float
    long_mv: float
    short_mv: float  # negative number
    unrealized_pnl: float  # over positions with a cost basis
    day_pnl: float

    @property
    def gross_exposure(self) -> float:
        """(long MV + |short MV|) / NAV."""
        return (self.long_mv - self.short_mv) / self.nav

    @property
    def net_exposure(self) -> float:
        return (self.long_mv + self.short_mv) / self.nav

    @property
    def day_return(self) -> float:
        """Day P&L as a fraction of yesterday's NAV (assumes no trades today)."""
        return self.day_pnl / self.prev_nav if self.prev_nav else np.nan

    @property
    def weights(self) -> pd.Series:
        return self.positions["weight"]


def value_portfolio(portfolio: Portfolio, last: pd.Series, prev_close: pd.Series) -> Valuation:
    """Value every position at `last`; day P&L is measured against `prev_close`.

    Raises ValueError if a position has no price or NAV is not positive (weights would be
    meaningless).
    """
    tickers = portfolio.tickers
    missing = [t for t in tickers if pd.isna(last.get(t)) or pd.isna(prev_close.get(t))]
    if missing:
        raise ValueError(f"no price for: {', '.join(missing)}")

    df = pd.DataFrame(
        {
            "quantity": [p.quantity for p in portfolio.positions],
            "avg_cost": [
                p.avg_cost if p.avg_cost is not None else np.nan for p in portfolio.positions
            ],
        },
        index=pd.Index(tickers, name="ticker"),
        dtype=float,
    )
    df["price"] = last.reindex(tickers).astype(float)
    df["prev_close"] = prev_close.reindex(tickers).astype(float)
    df["market_value"] = df["quantity"] * df["price"]
    df["cost_basis"] = df["quantity"] * df["avg_cost"]
    df["unrealized_pnl"] = (df["price"] - df["avg_cost"]) * df["quantity"]
    # Return on the position from the holder's perspective: a short gains when price falls.
    df["unrealized_pnl_pct"] = (df["price"] / df["avg_cost"] - 1) * np.sign(df["quantity"])
    df["day_pnl"] = (df["price"] - df["prev_close"]) * df["quantity"]
    df["day_change_pct"] = df["price"] / df["prev_close"] - 1

    nav = portfolio.cash + df["market_value"].sum()
    if nav <= 0:
        raise ValueError(f"NAV is {nav:,.0f}; weights require a positive NAV (add cash?)")
    prev_nav = portfolio.cash + (df["quantity"] * df["prev_close"]).sum()
    df["weight"] = df["market_value"] / nav

    mv = df["market_value"]
    return Valuation(
        positions=df,
        cash=portfolio.cash,
        nav=float(nav),
        prev_nav=float(prev_nav),
        long_mv=float(mv[mv > 0].sum()),
        short_mv=float(mv[mv < 0].sum()),
        unrealized_pnl=float(df["unrealized_pnl"].sum(skipna=True)),
        day_pnl=float(df["day_pnl"].sum()),
    )
