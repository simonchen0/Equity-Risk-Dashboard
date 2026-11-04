"""Yahoo Finance provider (unofficial API: delayed data, occasional rate limits)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from riskdash.data.provider import DataProviderError, SecurityMeta

log = logging.getLogger(__name__)

ETF_SECTOR = "Index / ETF"


class YFinanceProvider:
    def get_prices(self, tickers: Sequence[str], start: date, end: date) -> pd.DataFrame:
        tickers = sorted(set(tickers))
        if not tickers:
            return pd.DataFrame()
        try:
            raw = yf.download(
                tickers,
                start=start,
                end=end + timedelta(days=1),  # yfinance `end` is exclusive
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as exc:  # yfinance raises a wide variety of exception types
            raise DataProviderError(f"Price download failed: {exc}") from exc
        if raw is None or raw.empty:
            raise DataProviderError("Price download returned no data")
        closes = raw["Close"]
        if isinstance(closes, pd.Series):  # defensive: older single-level output
            closes = closes.to_frame(tickers[0])
        closes = closes.dropna(axis=1, how="all").sort_index()
        closes.index = pd.DatetimeIndex(closes.index).tz_localize(None)
        closes.columns.name = None
        return closes

    def get_meta(self, tickers: Sequence[str]) -> dict[str, SecurityMeta]:
        out: dict[str, SecurityMeta] = {}
        for t in sorted(set(tickers)):
            try:
                info = yf.Ticker(t).info or {}
            except Exception as exc:
                log.warning("Metadata lookup failed for %s: %s", t, exc)
                info = {}
            sector = info.get("sector")
            if sector is None and info.get("quoteType") == "ETF":
                sector = ETF_SECTOR
            out[t] = SecurityMeta(ticker=t, name=info.get("shortName"), sector=sector)
        return out
