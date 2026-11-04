"""Daily return construction."""

from __future__ import annotations

import pandas as pd

TRADING_DAYS = 252
LOOKBACKS = {"6M": 126, "1Y": 252, "2Y": 504}


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Simple (not log) daily returns: simple returns aggregate linearly across positions."""
    return prices.sort_index().pct_change(fill_method=None).iloc[1:]


def aligned_window(returns: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """The last `lookback` dates on which every column has a return.

    Using one common window keeps the covariance matrix positive semi-definite and makes
    betas, vols and correlations comparable. The cost: a recently listed stock shortens the
    window for everyone — callers should surface `len(result)` when it is below `lookback`.
    """
    return returns.dropna(how="any").tail(lookback)
