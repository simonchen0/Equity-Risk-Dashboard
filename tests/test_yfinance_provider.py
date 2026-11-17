"""YFinanceProvider against a stubbed yfinance (no network)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from riskdash.data import yfinance_provider as yp
from riskdash.data.provider import DataProviderError

START, END = date(2026, 10, 1), date(2026, 10, 9)


def raw_frame(**cols):
    idx = pd.date_range("2026-10-01", periods=3, freq="B", tz="America/New_York")
    return pd.concat({"Close": pd.DataFrame(cols, index=idx)}, axis=1)


def test_prices_are_cleaned(monkeypatch):
    raw = raw_frame(AAA=[1.0, 2.0, 3.0], BBB=[np.nan] * 3, SPY=[4.0, 5.0, 6.0])
    monkeypatch.setattr(yp.yf, "download", lambda *a, **k: raw)
    out = yp.YFinanceProvider().get_prices(["SPY", "AAA", "BBB"], START, END)
    assert list(out.columns) == ["AAA", "SPY"]  # all-NaN ticker dropped
    assert out.index.tz is None and out.index.is_monotonic_increasing


def test_download_end_is_made_inclusive(monkeypatch):
    seen = {}

    def fake(tickers, **kw):
        seen.update(kw)
        return raw_frame(AAA=[1.0, 2.0, 3.0])

    monkeypatch.setattr(yp.yf, "download", fake)
    yp.YFinanceProvider().get_prices(["AAA"], START, END)
    assert seen["end"] == date(2026, 10, 10) and seen["auto_adjust"] is True


@pytest.mark.parametrize("result", [pd.DataFrame(), None])
def test_empty_download_is_an_error(monkeypatch, result):
    monkeypatch.setattr(yp.yf, "download", lambda *a, **k: result)
    with pytest.raises(DataProviderError):
        yp.YFinanceProvider().get_prices(["AAA"], START, END)


def test_vendor_exception_is_wrapped(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(yp.yf, "download", boom)
    with pytest.raises(DataProviderError, match="rate limited"):
        yp.YFinanceProvider().get_prices(["AAA"], START, END)


def test_no_tickers_returns_empty_frame():
    assert yp.YFinanceProvider().get_prices([], START, END).empty


def test_meta_etf_fallback_and_failure(monkeypatch):
    infos = {"AAA": {"shortName": "Alpha", "sector": "Technology"}, "SPY": {"quoteType": "ETF"}}

    class FakeTicker:
        def __init__(self, t):
            self.t = t

        @property
        def info(self):
            if self.t == "BAD":
                raise RuntimeError("no info")
            return infos[self.t]

    monkeypatch.setattr(yp.yf, "Ticker", FakeTicker)
    meta = yp.YFinanceProvider().get_meta(["AAA", "SPY", "BAD"])
    assert meta["AAA"].sector == "Technology" and meta["AAA"].name == "Alpha"
    assert meta["SPY"].sector == yp.ETF_SECTOR
    assert meta["BAD"].sector is None and meta["BAD"].name is None  # failure, not a crash
