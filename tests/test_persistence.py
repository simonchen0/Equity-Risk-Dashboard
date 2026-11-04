import json

import pytest

from riskdash.alerts.limits import load_limits
from riskdash.persistence import SavedState, load_state, save_state, state_path
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


def test_round_trip_restores_everything(tmp_path, pf):
    path = tmp_path / "state.json"
    limits = load_limits().model_copy(update={"max_single_name_weight": 0.07})
    save_state(pf, limits, "2Y", True, path)
    saved = load_state(path, LOOKBACKS)
    assert saved == SavedState(pf, limits, "2Y", True)


def test_save_creates_missing_directory_and_leaves_no_temp_file(tmp_path, pf):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_state(pf, load_limits(), "1Y", False, path)
    assert path.exists()
    assert [p.name for p in path.parent.iterdir()] == ["state.json"]


def test_missing_file_gives_defaults(tmp_path):
    assert load_state(tmp_path / "nope.json") == SavedState()


@pytest.mark.parametrize("content", ["", "not json", "[1, 2]", '"text"'])
def test_corrupt_file_gives_defaults(tmp_path, content):
    path = tmp_path / "state.json"
    path.write_text(content)
    assert load_state(path) == SavedState()


def test_invalid_part_does_not_discard_the_rest(tmp_path, pf):
    path = tmp_path / "state.json"
    save_state(pf, load_limits(), "6M", True, path)
    raw = json.loads(path.read_text())
    raw["portfolio"]["positions"][0]["quantity"] = 0  # invalid: zero quantity
    raw["limits"]["unknown_key"] = 1  # invalid: limits reject unknown keys
    path.write_text(json.dumps(raw))
    saved = load_state(path, LOOKBACKS)
    assert saved.portfolio is None and saved.limits is None
    assert saved.lookback == "6M" and saved.blume is True


def test_unknown_lookback_and_non_bool_blume_are_ignored(tmp_path, pf):
    path = tmp_path / "state.json"
    save_state(pf, load_limits(), "1Y", False, path)
    raw = json.loads(path.read_text())
    raw["lookback"], raw["blume"] = "10Y", "yes"
    path.write_text(json.dumps(raw))
    saved = load_state(path, LOOKBACKS)
    assert saved.lookback is None and saved.blume is None


def test_unwritable_location_does_not_raise(tmp_path, pf):
    blocker = tmp_path / "file"
    blocker.write_text("x")  # a file where a directory is needed
    save_state(pf, load_limits(), "1Y", False, blocker / "state.json")


def test_persistence_can_be_disabled_and_path_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("RISKDASH_PERSIST", "0")
    assert state_path() is None
    monkeypatch.setenv("RISKDASH_PERSIST", "1")
    monkeypatch.setenv("RISKDASH_STATE_FILE", str(tmp_path / "custom.json"))
    assert state_path() == tmp_path / "custom.json"
    monkeypatch.delenv("RISKDASH_STATE_FILE")
    assert state_path().name == "state.json"
