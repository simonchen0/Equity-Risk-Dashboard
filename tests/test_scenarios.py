import numpy as np
import pandas as pd
import pytest

from riskdash.analytics.beta import dollar_beta
from riskdash.analytics.scenarios import position_pnl, scenario_grid

SHOCKS = [-0.10, -0.05, 0.0, 0.05, 0.10]


@pytest.fixture
def book():
    mv = pd.Series({"A": 600_000.0, "B": -200_000.0, "C": 100_000.0})
    betas = pd.Series({"A": 1.5, "B": 0.8, "C": 0.0})
    return mv, betas


def test_hand_computed_pnl(book):
    mv, betas = book
    pnl = position_pnl(mv, betas, [-0.10])
    assert pnl.loc["A", -0.10] == pytest.approx(600_000 * 1.5 * -0.10)  # -90,000
    assert pnl.loc["B", -0.10] == pytest.approx(16_000)  # short gains when market falls
    assert pnl.loc["C", -0.10] == 0  # zero beta


def test_total_equals_dollar_beta_times_shock(book):
    mv, betas = book
    grid = scenario_grid(mv, betas, nav=1_000_000, shocks=SHOCKS)
    for shock in SHOCKS:
        assert grid.loc[shock, "pnl"] == pytest.approx(dollar_beta(mv, betas) * shock)


def test_pnl_is_linear_and_antisymmetric(book):
    mv, betas = book
    grid = scenario_grid(mv, betas, 1_000_000, SHOCKS)
    assert grid.loc[0.0, "pnl"] == 0
    assert grid.loc[-0.10, "pnl"] == pytest.approx(-grid.loc[0.10, "pnl"])
    assert grid.loc[0.10, "pnl"] == pytest.approx(2 * grid.loc[0.05, "pnl"])


def test_positions_sum_to_total(book):
    mv, betas = book
    pnl = position_pnl(mv, betas, SHOCKS)
    grid = scenario_grid(mv, betas, 1_000_000, SHOCKS)
    assert np.allclose(pnl.sum(), grid["pnl"])


def test_zero_beta_book_has_no_pnl():
    mv = pd.Series({"A": 1e6, "B": -5e5})
    grid = scenario_grid(mv, pd.Series({"A": 0.0, "B": 0.0}), 1e6, SHOCKS)
    assert (grid["pnl"] == 0).all()


def test_pnl_pct_nav_uses_nav_not_gross(book):
    mv, betas = book
    grid = scenario_grid(mv, betas, nav=500_000, shocks=[-0.10])
    assert grid.loc[-0.10, "pnl_pct_nav"] == pytest.approx(grid.loc[-0.10, "pnl"] / 500_000)


def test_missing_beta_propagates_nan_not_zero():
    mv = pd.Series({"A": 1e6, "B": 1e6})
    pnl = position_pnl(mv, pd.Series({"A": 1.0}), [-0.1])
    assert np.isnan(pnl.loc["B", -0.1]) and pnl.loc["A", -0.1] == pytest.approx(-100_000)


def test_grid_total_is_nan_when_any_beta_missing():
    mv = pd.Series({"A": 1e6, "B": 1e6})
    grid = scenario_grid(mv, pd.Series({"A": 1.0}), 2e6, [-0.1])
    assert np.isnan(grid.loc[-0.1, "pnl"])
