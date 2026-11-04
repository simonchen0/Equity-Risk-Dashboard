"""Beta-implied S&P 500 scenario analysis.

P&L_i(shock) = market_value_i * beta_i * shock. This is a linear, systematic-only estimate:
it ignores stock-specific moves, convexity, and changes in beta during large moves.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

DEFAULT_SHOCKS = (-0.20, -0.15, -0.10, -0.05, -0.025, 0.0, 0.025, 0.05, 0.10, 0.15, 0.20)


def position_pnl(
    market_values: pd.Series, betas: pd.Series, shocks: Sequence[float]
) -> pd.DataFrame:
    """P&L per position (rows) for each S&P 500 shock (columns, as fractions: -0.10 = -10%)."""
    exposure = market_values * betas.reindex(market_values.index)  # dollar beta per position
    return pd.DataFrame(
        np.outer(exposure.to_numpy(dtype=float), np.asarray(shocks, dtype=float)),
        index=market_values.index,
        columns=pd.Index(list(shocks), name="shock"),
    )


def scenario_grid(
    market_values: pd.Series, betas: pd.Series, nav: float, shocks: Sequence[float]
) -> pd.DataFrame:
    """Total portfolio P&L ($) and return on NAV (fraction) for each shock."""
    pnl = position_pnl(market_values, betas, shocks)
    total = pnl.sum(
        min_count=len(pnl)
    )  # NaN, not a silently understated total, if any beta is missing
    return pd.DataFrame({"pnl": total, "pnl_pct_nav": total / nav})
