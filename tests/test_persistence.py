import json

import pytest

from riskdash.alerts.limits import load_limits
from riskdash.persistence import SavedState, dump_state, parse_state
from riskdash.portfolio.models import Portfolio, Position

LOOKBACKS = ("6M", "1Y", "2Y")


@pytest.fixture
def pf():
    return Portfolio(
        positions=[
            Position(ticker="AAPL", quantity=100, avg_cost=150.0, sector="Technology"),
            Position(ticker="TSLA", quantity=-50),
        ],
        cash=12_345.67,
    )


def test_round_trip_restores_everything(pf):
    limits = load_limits().model_copy(update={"max_single_name_weight": 0.07})
    saved = parse_state(dump_state(pf, limits, "2Y", True), LOOKBACKS)
    assert saved == SavedState(pf, limits, "2Y", True)


@pytest.mark.parametrize("text", [None, "", "not json", "[1, 2]", '"text"'])
def test_missing_or_corrupt_gives_defaults(text):
    assert parse_state(text) == SavedState()


def test_invalid_part_does_not_discard_the_rest(pf):
    raw = json.loads(dump_state(pf, load_limits(), "6M", True))
    raw["portfolio"]["positions"][0]["quantity"] = 0  # invalid: zero quantity
    raw["limits"]["unknown_key"] = 1  # invalid: limits reject unknown keys
    saved = parse_state(json.dumps(raw), LOOKBACKS)
    assert saved.portfolio is None and saved.limits is None
    assert saved.lookback == "6M" and saved.blume is True


def test_unknown_lookback_and_non_bool_blume_are_ignored(pf):
    raw = json.loads(dump_state(pf, load_limits(), "1Y", False))
    raw["lookback"], raw["blume"] = "10Y", "yes"
    saved = parse_state(json.dumps(raw), LOOKBACKS)
    assert saved.lookback is None and saved.blume is None
