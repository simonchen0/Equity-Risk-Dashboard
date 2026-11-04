"""Session state, cached market data, and the per-rerun risk snapshot."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from riskdash.analytics.returns import LOOKBACKS
from riskdash.data.cache import CachedProvider
from riskdash.data.provider import DataProviderError, SecurityMeta
from riskdash.data.yfinance_provider import YFinanceProvider
from riskdash.engine import RiskSnapshot, build_snapshot
from riskdash.portfolio.io import read_portfolio_csv
from riskdash.portfolio.models import Portfolio

ROOT = Path(__file__).resolve().parents[2]
DEMO_CSV = ROOT / "data" / "sample_portfolio.csv"


@st.cache_resource
def _vendor() -> CachedProvider:
    return CachedProvider(YFinanceProvider())


@st.cache_data(ttl=15 * 60, show_spinner="Loading market data…")
def _prices(tickers: tuple[str, ...], start: date, end: date) -> tuple[pd.DataFrame, bool]:
    vendor = _vendor()
    df = vendor.get_prices(tickers, start, end)
    return df, vendor.served_stale


@st.cache_data(ttl=24 * 3600, show_spinner="Loading security details…")
def _meta(tickers: tuple[str, ...]) -> dict[str, SecurityMeta]:
    return _vendor().get_meta(tickers)


class AppProvider:
    """Provider facade that routes through Streamlit's cache (shared across sessions)."""

    def __init__(self) -> None:
        self.stale = False

    def get_prices(self, tickers: Sequence[str], start: date, end: date) -> pd.DataFrame:
        df, stale = _prices(tuple(sorted(set(tickers))), start, end)
        self.stale = self.stale or stale
        return df

    def get_meta(self, tickers: Sequence[str]) -> dict[str, SecurityMeta]:
        return _meta(tuple(sorted(set(tickers))))


def init_state() -> None:
    ss = st.session_state
    if "portfolio" not in ss:
        ss.portfolio = read_portfolio_csv(DEMO_CSV)
        ss.portfolio_version = 0  # bump to reset widgets bound to the old portfolio
    ss.setdefault("lookback_label", "1Y")
    ss.setdefault("blume", False)


def get_portfolio() -> Portfolio:
    return st.session_state.portfolio


def set_portfolio(portfolio: Portfolio) -> None:
    st.session_state.portfolio = portfolio
    st.session_state.portfolio_version += 1


def load_demo() -> None:
    set_portfolio(read_portfolio_csv(DEMO_CSV))


def snapshot() -> tuple[RiskSnapshot | None, str | None, bool]:
    """(snapshot, error message, served-stale-data flag) for the current settings."""
    provider = AppProvider()
    try:
        snap = build_snapshot(
            get_portfolio(),
            provider,
            lookback=LOOKBACKS[st.session_state.lookback_label],
            blume=st.session_state.blume,
        )
    except DataProviderError as exc:
        return None, f"Market data is unavailable right now ({exc}). Try again shortly.", False
    except ValueError as exc:
        return None, str(exc), provider.stale
    return snap, None, provider.stale


def require_snapshot() -> RiskSnapshot:
    """Render data errors/warnings and the as-of caption; stop the page if there is no snapshot."""
    snap, error, stale = snapshot()
    if error:
        st.error(error)
        st.page_link("views/positions.py", label="Edit positions", icon=":material/edit_note:")
        st.stop()
    if stale:
        st.warning("Live data unavailable — showing the most recent cached prices.")
    for w in snap.warnings:
        st.warning(w)
    st.caption(
        f"Prices as of close {snap.as_of:%a %d %b %Y} (or latest intraday print) · "
        f"risk over {snap.n_obs} trading days · beta vs SPY"
        + (" (Blume-adjusted)" if st.session_state.blume else "")
    )
    return snap


def sector_map(tickers: Sequence[str]) -> dict[str, str]:
    """Manual override wins over the vendor sector."""
    overrides = {p.ticker: p.sector for p in get_portfolio().positions if p.sector}
    meta = AppProvider().get_meta(tickers)
    return {
        t: overrides.get(t) or meta.get(t, SecurityMeta(t)).sector or "Unclassified"
        for t in tickers
    }


def names(tickers: Sequence[str]) -> dict[str, str]:
    meta = AppProvider().get_meta(tickers)
    return {t: meta.get(t, SecurityMeta(t)).name or t for t in tickers}
