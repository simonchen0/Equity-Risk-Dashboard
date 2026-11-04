"""Index hedge sizing: how much SPY / S&P 500 futures to trade to reach a target beta.

Assumptions: the hedge instrument moves one-for-one with the S&P 500 (`hedge_beta` = 1).
Basis, futures carry, dividends, financing and margin are ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from riskdash.analytics.beta import BENCHMARK

ES_MULTIPLIER = 50  # E-mini S&P 500: $50 per index point
MES_MULTIPLIER = 5  # Micro E-mini S&P 500: $5 per index point


@dataclass(frozen=True)
class HedgeSizing:
    exact_units: float  # signed; negative = sell/short
    units: int  # rounded to whole shares/contracts
    unit_notional: float  # dollars of S&P exposure per share/contract
    notional: float  # units * unit_notional (signed)
    post_beta: float  # portfolio beta after trading `units`
    residual_beta: float  # post_beta - target_beta, from rounding to whole units


def required_notional(
    target_beta: float, portfolio_beta: float, nav: float, hedge_beta: float = 1.0
) -> float:
    """Signed dollar exposure to add: (target - current) * NAV / hedge beta.

    Negative means sell (short) the hedge instrument to reduce beta.
    """
    if nav <= 0:
        raise ValueError("NAV must be positive")
    if hedge_beta == 0:
        raise ValueError("hedge beta must be non-zero")
    return (target_beta - portfolio_beta) * nav / hedge_beta


def _round_half_away(x: float) -> int:
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def hedged_beta(
    portfolio_beta: float, nav: float, notional: float, hedge_beta: float = 1.0
) -> float:
    """Portfolio beta after adding `notional` dollars of the hedge instrument."""
    return portfolio_beta + notional * hedge_beta / nav


def size_hedge(
    target_beta: float,
    portfolio_beta: float,
    nav: float,
    unit_notional: float,
    hedge_beta: float = 1.0,
) -> HedgeSizing:
    """Whole-unit hedge for one instrument, with the beta left over from rounding."""
    if unit_notional <= 0:
        raise ValueError("unit notional must be positive")
    exact = required_notional(target_beta, portfolio_beta, nav, hedge_beta) / unit_notional
    units = _round_half_away(exact)
    notional = units * unit_notional
    post = hedged_beta(portfolio_beta, nav, notional, hedge_beta)
    return HedgeSizing(exact, units, unit_notional, notional, post, post - target_beta)


def hedged_weights(weights: pd.Series, notional: float, nav: float) -> pd.Series:
    """Position weights with the hedge added to SPY (the hedge tracks SPY's returns)."""
    w = weights.copy()
    w[BENCHMARK] = w.get(BENCHMARK, 0.0) + notional / nav
    return w


def hedged_vol(weights: pd.Series, notional: float, nav: float, cov: pd.DataFrame) -> float:
    """Annualized portfolio volatility after the hedge; `cov` must include SPY."""
    w = hedged_weights(weights, notional, nav)
    sigma = cov.loc[w.index, w.index].to_numpy(dtype=float)
    v = w.to_numpy(dtype=float)
    return float(np.sqrt(max(v @ sigma @ v, 0.0)))
