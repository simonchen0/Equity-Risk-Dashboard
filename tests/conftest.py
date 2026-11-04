import numpy as np
import pandas as pd
import pytest

from riskdash.data.fixture_provider import FixtureProvider
from riskdash.data.provider import SecurityMeta


def make_prices(betas: dict[str, float], n: int = 400, seed: int = 7, idio: float = 0.01):
    """Synthetic adjusted closes where r_i = beta_i * r_SPY + idiosyncratic noise."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2026-10-30", periods=n + 1)
    r_m = rng.normal(0.0004, 0.01, n)
    rets = {"SPY": r_m}
    for t, b in betas.items():
        rets[t] = b * r_m + rng.normal(0, idio, n)
    r = pd.DataFrame(rets, index=dates[1:])
    prices = 100 * (1 + r).cumprod()
    first = pd.DataFrame(100.0, index=dates[:1], columns=r.columns)
    return pd.concat([first, prices])


@pytest.fixture
def synthetic_prices():
    return make_prices({"AAA": 1.5, "BBB": 0.5, "CCC": 1.0})


@pytest.fixture
def provider(synthetic_prices):
    meta = {
        "AAA": SecurityMeta("AAA", "Alpha Inc", "Technology"),
        "BBB": SecurityMeta("BBB", "Beta Corp", "Utilities"),
        "CCC": SecurityMeta("CCC", "Gamma Co", "Financial Services"),
    }
    return FixtureProvider(synthetic_prices, meta)
