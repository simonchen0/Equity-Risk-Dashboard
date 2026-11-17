"""Volatility and risk decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd

from riskdash.analytics.returns import TRADING_DAYS


def annualized_vol(returns: pd.DataFrame) -> pd.Series:
    return returns.std(ddof=1) * np.sqrt(TRADING_DAYS)


def annualized_cov(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.cov(ddof=1) * TRADING_DAYS


def one_day_move(annual_vol: float, nav: float) -> float:
    """Typical (1 standard deviation) one-day move in NAV, in dollars.

    Scales annual volatility by sqrt(252) and assumes normally distributed returns. This is a
    volatility estimate from history, not a Value-at-Risk figure or a forecast.
    """
    return annual_vol / np.sqrt(TRADING_DAYS) * nav


def portfolio_vol(weights: pd.Series, cov: pd.DataFrame) -> float:
    """sqrt(w' Σ w) with NAV weights, so the result is volatility of NAV returns."""
    w = weights.to_numpy(dtype=float)
    sigma = cov.loc[weights.index, weights.index].to_numpy(dtype=float)
    return float(np.sqrt(max(w @ sigma @ w, 0.0)))


def risk_contributions(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Fraction of portfolio variance from each position: w_i (Σw)_i / (w'Σw). Sums to 1.

    Can be negative for a position that diversifies (e.g. a short in a correlated book).
    """
    w = weights.to_numpy(dtype=float)
    sigma = cov.loc[weights.index, weights.index].to_numpy(dtype=float)
    total = w @ sigma @ w
    if total <= 0:
        return pd.Series(np.nan, index=weights.index)
    return pd.Series(w * (sigma @ w) / total, index=weights.index)
