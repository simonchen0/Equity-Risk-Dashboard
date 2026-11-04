"""In-memory provider backed by a price DataFrame. Used by tests and offline demos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from riskdash.data.provider import SecurityMeta


class FixtureProvider:
    def __init__(self, prices: pd.DataFrame, meta: dict[str, SecurityMeta] | None = None):
        self._prices = prices.sort_index()
        self._meta = meta or {}

    @classmethod
    def from_csv(
        cls, prices_csv: str | Path, meta_csv: str | Path | None = None
    ) -> FixtureProvider:
        prices = pd.read_csv(prices_csv, index_col=0, parse_dates=True)
        meta: dict[str, SecurityMeta] = {}
        if meta_csv is not None:
            for row in pd.read_csv(meta_csv).itertuples(index=False):
                meta[row.ticker] = SecurityMeta(row.ticker, row.name, row.sector)
        return cls(prices, meta)

    def get_prices(self, tickers: Sequence[str], start: date, end: date) -> pd.DataFrame:
        cols = [t for t in dict.fromkeys(tickers) if t in self._prices.columns]
        window = self._prices.loc[pd.Timestamp(start) : pd.Timestamp(end), cols]
        return window.dropna(axis=1, how="all")

    def get_meta(self, tickers: Sequence[str]) -> dict[str, SecurityMeta]:
        return {t: self._meta.get(t, SecurityMeta(t)) for t in tickers}
