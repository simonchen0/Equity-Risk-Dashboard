"""Orchestrates data -> valuation -> risk into one snapshot the UI renders.

UI-free and network-free given a provider, so it is tested end-to-end with FixtureProvider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from riskdash.analytics import beta as beta_mod
from riskdash.analytics.returns import TRADING_DAYS, aligned_window, daily_returns
from riskdash.analytics.volatility import (
    annualized_cov,
    annualized_vol,
    portfolio_vol,
    risk_contributions,
)
from riskdash.data.provider import MarketDataProvider
from riskdash.portfolio.models import Portfolio
from riskdash.portfolio.valuation import Valuation, value_portfolio

BENCHMARK = beta_mod.BENCHMARK
MIN_OBS = 60  # below this, betas and vols are too noisy to display without a warning


@dataclass
class RiskSnapshot:
    valuation: Valuation
    as_of: pd.Timestamp
    lookback: int
    n_obs: int
    returns: pd.DataFrame  # aligned window; securities + benchmark
    betas: pd.Series  # per position (raw or Blume-adjusted)
    r_squared: pd.Series
    position_vol: pd.Series
    cov: pd.DataFrame  # annualized, positions only
    portfolio_beta: float
    dollar_beta: float
    portfolio_vol: float
    risk_contrib: pd.Series
    excluded: list[str] = field(default_factory=list)  # tickers with no market data
    warnings: list[str] = field(default_factory=list)

    @property
    def positions(self) -> pd.DataFrame:
        """Valuation table joined with per-position risk columns."""
        df = self.valuation.positions.copy()
        df["beta"] = self.betas
        df["beta_adj_exposure"] = df["weight"] * df["beta"]
        df["vol"] = self.position_vol
        df["risk_contrib"] = self.risk_contrib
        return df


def excluded_warning(excluded: list[str]) -> str:
    """The message for tickers that returned no market data."""
    return (
        f"No market data for {', '.join(excluded)} — excluded from NAV and risk. "
        "Check the ticker symbols."
    )


def fetch_window(lookback: int, today: date) -> tuple[date, date]:
    """Calendar range that covers `lookback` trading days plus a buffer for holidays."""
    calendar_days = int(lookback * 365 / TRADING_DAYS) + 21
    return today - timedelta(days=calendar_days), today


def build_snapshot(
    portfolio: Portfolio,
    provider: MarketDataProvider,
    lookback: int = TRADING_DAYS,
    blume: bool = False,
    today: date | None = None,
) -> RiskSnapshot:
    if not portfolio.positions:
        raise ValueError("portfolio has no positions")
    start, end = fetch_window(lookback, today or date.today())
    tickers = portfolio.tickers
    prices = provider.get_prices(list(dict.fromkeys([*tickers, BENCHMARK])), start, end)
    if BENCHMARK not in prices.columns:
        raise ValueError(f"no data for benchmark {BENCHMARK}")

    warnings: list[str] = []
    excluded = [t for t in tickers if t not in prices.columns]
    if excluded:
        warnings.append(excluded_warning(excluded))
        portfolio = Portfolio(
            positions=[p for p in portfolio.positions if p.ticker not in excluded],
            cash=portfolio.cash,
        )
        if not portfolio.positions:
            raise ValueError("none of the portfolio's tickers returned market data")
    tickers = portfolio.tickers

    # Last and previous close per ticker, robust to a ticker missing today's print.
    last = prices.apply(lambda s: s.dropna().iloc[-1] if s.notna().sum() else np.nan)
    prev = prices.apply(lambda s: s.dropna().iloc[-2] if s.notna().sum() > 1 else np.nan)
    valuation = value_portfolio(portfolio, last, prev)

    cols = list(dict.fromkeys([*tickers, BENCHMARK]))  # dedupe: the book may hold SPY itself
    rets = aligned_window(daily_returns(prices[cols]), lookback)
    n_obs = len(rets)
    if n_obs < MIN_OBS:
        raise ValueError(f"only {n_obs} common return observations; need at least {MIN_OBS}")
    if n_obs < lookback * 0.9:
        shortest = prices[tickers].notna().sum().idxmin()
        warnings.append(
            f"Risk uses {n_obs} trading days instead of {lookback}: {shortest} has the "
            "shortest price history and limits the common window."
        )

    raw_betas = beta_mod.betas(rets)[tickers]
    betas = beta_mod.blume_adjust(raw_betas) if blume else raw_betas
    weights = valuation.weights
    cov = annualized_cov(rets[tickers])

    return RiskSnapshot(
        valuation=valuation,
        as_of=prices.index[-1],
        lookback=lookback,
        n_obs=n_obs,
        returns=rets,
        betas=betas,
        r_squared=beta_mod.r_squared(rets)[tickers],
        position_vol=annualized_vol(rets[tickers]),
        cov=cov,
        portfolio_beta=beta_mod.portfolio_beta(weights, betas),
        dollar_beta=beta_mod.dollar_beta(valuation.positions["market_value"], betas),
        portfolio_vol=portfolio_vol(weights, cov),
        risk_contrib=risk_contributions(weights, cov),
        excluded=excluded,
        warnings=warnings,
    )
