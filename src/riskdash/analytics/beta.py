"""Market beta vs the benchmark (SPY)."""

from __future__ import annotations

import pandas as pd

BENCHMARK = "SPY"


def betas(returns: pd.DataFrame, benchmark: str = BENCHMARK) -> pd.Series:
    """OLS slope of each column's daily returns on the benchmark's: cov(r_i, r_m) / var(r_m).

    Raw (not excess) returns: at a daily horizon the risk-free rate is negligible.
    """
    if benchmark not in returns.columns:
        raise ValueError(f"benchmark {benchmark} missing from returns")
    m = returns[benchmark]
    var_m = m.var(ddof=1)
    if not var_m > 0:
        raise ValueError("benchmark return variance is zero; need more history")
    return returns.apply(lambda col: col.cov(m, ddof=1) / var_m)


def r_squared(returns: pd.DataFrame, benchmark: str = BENCHMARK) -> pd.Series:
    """Share of each column's variance explained by the market (= squared correlation)."""
    return returns.corrwith(returns[benchmark]) ** 2


def blume_adjust(beta: pd.Series | float) -> pd.Series | float:
    """Blume (1971) shrinkage toward 1, as used by Bloomberg's 'adjusted beta'."""
    return 0.67 * beta + 0.33


def portfolio_beta(weights: pd.Series, beta: pd.Series) -> float:
    """sum(w_i * beta_i) with weights as a fraction of NAV; cash contributes zero beta."""
    return float((weights * beta.reindex(weights.index)).sum(min_count=len(weights)))


def dollar_beta(market_values: pd.Series, beta: pd.Series) -> float:
    """Beta-weighted dollar exposure: the P&L per 1.00 (=100%) move in the S&P 500."""
    return float(
        (market_values * beta.reindex(market_values.index)).sum(min_count=len(market_values))
    )
