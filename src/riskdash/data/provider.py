"""Market data provider interface.

Every data source (yfinance, fixtures, a future paid API) implements this protocol so the
analytics and the app never depend on a specific vendor.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class SecurityMeta:
    ticker: str
    name: str | None = None
    sector: str | None = None


class MarketDataProvider(Protocol):
    def get_prices(self, tickers: Sequence[str], start: date, end: date) -> pd.DataFrame:
        """Daily split- and dividend-adjusted closes.

        Index: ascending DatetimeIndex. Columns: the tickers that returned data (tickers
        with no data are omitted, never returned as all-NaN columns). `end` is inclusive.
        """
        ...

    def get_meta(self, tickers: Sequence[str]) -> dict[str, SecurityMeta]:
        """Name and sector per ticker. Unknown tickers map to a SecurityMeta with None fields."""
        ...


class DataProviderError(RuntimeError):
    """Raised when a provider cannot return data (network failure, vendor outage)."""
