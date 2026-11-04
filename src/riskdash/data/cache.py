"""Disk cache wrapper for any provider.

Fresh entries are served without calling the vendor; if the vendor fails, the most recent
cached copy is served even when stale, so a yfinance outage degrades instead of crashing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from riskdash.data.provider import DataProviderError, MarketDataProvider, SecurityMeta

log = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "riskdash"


class CachedProvider:
    def __init__(
        self,
        inner: MarketDataProvider,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        price_ttl_s: float = 15 * 60,
        meta_ttl_s: float = 7 * 24 * 3600,
    ):
        self.inner = inner
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.price_ttl_s = price_ttl_s
        self.meta_ttl_s = meta_ttl_s
        self.served_stale = False  # set when the last call fell back to stale data

    @staticmethod
    def _key(*parts: object) -> str:
        return hashlib.sha256(json.dumps(parts, default=str).encode()).hexdigest()[:24]

    def _fresh(self, path: Path, ttl: float) -> bool:
        return path.exists() and time.time() - path.stat().st_mtime < ttl

    def get_prices(self, tickers: Sequence[str], start: date, end: date) -> pd.DataFrame:
        tickers = sorted(set(tickers))
        path = self.dir / f"prices_{self._key(tickers, start, end)}.parquet"
        self.served_stale = False
        if self._fresh(path, self.price_ttl_s):
            return pd.read_parquet(path)
        try:
            df = self.inner.get_prices(tickers, start, end)
        except DataProviderError:
            stale = self._latest_stale(tickers)
            if stale is None:
                raise
            log.warning("Vendor failed; serving stale cached prices")
            self.served_stale = True
            return stale.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        df.to_parquet(path)
        df.to_parquet(self._stale_path(tickers))
        return df

    def _stale_path(self, tickers: list[str]) -> Path:
        return self.dir / f"prices_latest_{self._key(tickers)}.parquet"

    def _latest_stale(self, tickers: list[str]) -> pd.DataFrame | None:
        path = self._stale_path(tickers)
        return pd.read_parquet(path) if path.exists() else None

    def get_meta(self, tickers: Sequence[str]) -> dict[str, SecurityMeta]:
        out: dict[str, SecurityMeta] = {}
        missing: list[str] = []
        for t in tickers:
            path = self.dir / f"meta_{self._key(t)}.json"
            if self._fresh(path, self.meta_ttl_s):
                out[t] = SecurityMeta(**json.loads(path.read_text()))
            else:
                missing.append(t)
        if missing:
            for t, meta in self.inner.get_meta(missing).items():
                out[t] = meta
                if meta.name or meta.sector:  # don't cache failed lookups
                    (self.dir / f"meta_{self._key(t)}.json").write_text(json.dumps(asdict(meta)))
        return out
