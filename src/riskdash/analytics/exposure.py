"""Sector exposure."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

UNCLASSIFIED = "Unclassified"


def sector_exposure(
    weights: pd.Series,
    sectors: Mapping[str, str],
    betas: pd.Series | None = None,
    risk_contrib: pd.Series | None = None,
) -> pd.DataFrame:
    """Long, short, net and gross weight per sector (fractions of NAV), sorted by gross.

    Optional columns: `beta_adj` (Σ w·β, the sector's contribution to portfolio beta) and
    `risk_contrib` (the sector's share of portfolio variance).
    """
    df = pd.DataFrame({"weight": weights})
    df["sector"] = [sectors.get(t) or UNCLASSIFIED for t in df.index]
    df["long"] = df["weight"].clip(lower=0)
    df["short"] = df["weight"].clip(upper=0)
    if betas is not None:
        df["beta_adj"] = df["weight"] * betas.reindex(df.index)
    if risk_contrib is not None:
        df["risk_contrib"] = risk_contrib.reindex(df.index)

    g = df.groupby("sector")
    out = pd.DataFrame(
        {
            "long": g["long"].sum(),
            "short": g["short"].sum(),
            "net": g["weight"].sum(),
            "gross": g["weight"].apply(lambda w: w.abs().sum()),
            "positions": g.size(),
        }
    )
    for col in ("beta_adj", "risk_contrib"):
        if col in df:
            out[col] = g[col].sum(min_count=1)
    return out.sort_values("gross", ascending=False)
