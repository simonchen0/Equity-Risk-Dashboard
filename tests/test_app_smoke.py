"""Render every page against synthetic prices (no network) and fail on any exception."""

import sys
from pathlib import Path

import pandas as pd
import pytest
from conftest import make_prices
from streamlit.testing.v1 import AppTest

from riskdash.data.cache import CachedProvider
from riskdash.data.fixture_provider import FixtureProvider
from riskdash.data.provider import SecurityMeta
from riskdash.portfolio.io import read_portfolio_csv

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["overview", "risk", "scenarios", "hedging", "alerts", "positions"]


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(ROOT / "app"))
    for mod in [m for m in sys.modules if m == "components" or m.startswith("components.")]:
        del sys.modules[mod]  # re-import so the patch below applies
    from components import state

    demo = read_portfolio_csv(ROOT / "data" / "sample_portfolio.csv")
    tickers = [p.ticker for p in demo.positions]
    betas = {t: 0.6 + 0.07 * i for i, t in enumerate(tickers)}
    # End today: pages that fetch the latest price (hedging) ask for a recent window.
    prices = make_prices(betas, end=pd.Timestamp.today().normalize())
    prices["ES=F"] = prices["SPY"] * 10
    provider = FixtureProvider(
        prices, {t: SecurityMeta(t, t, f"Sector{i % 4}") for i, t in enumerate(tickers)}
    )
    vendor = CachedProvider(provider, cache_dir=tmp_path)
    monkeypatch.setattr(state, "_vendor", lambda: vendor)
    state._prices.clear()
    state._meta.clear()
    monkeypatch.setattr(
        state,
        "LocalStorage",
        lambda: type("L", (), {"getItem": lambda *a: None, "setItem": lambda *a, **k: None})(),
    )
    return AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exceptions(app, page):
    app.run()
    if page != "overview":
        app.switch_page(f"views/{page}.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
