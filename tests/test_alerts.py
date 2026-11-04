from datetime import date

import pandas as pd
import pytest
import yaml
from pydantic import ValidationError

from riskdash.alerts.limits import DEFAULT_LIMITS_PATH, Limits, load_limits
from riskdash.alerts.rules import (
    BREACH,
    OK,
    WARN,
    RiskMetrics,
    evaluate,
    metrics_from_snapshot,
    severity,
)
from riskdash.engine import build_snapshot
from riskdash.portfolio.models import Portfolio, Position

LIMITS = Limits(
    max_single_name_weight=0.10,
    max_sector_net_weight=0.30,
    max_top5_weight=0.50,
    beta_min=0.0,
    beta_max=1.0,
    max_volatility=0.15,
    max_gross_exposure=1.5,
    max_abs_net_exposure=1.0,
    max_pair_correlation=0.85,
    correlation_min_weight=0.03,
    warn_fraction=0.8,
)


def metrics(weights, sectors=None, beta=0.5, vol=0.10, gross=None, net=None, corr=None):
    w = pd.Series(weights, dtype=float)
    if sectors is None:  # default: one sector per name
        sectors = {t: f"S_{t}" for t in w.index}
    if corr is None:
        corr = pd.DataFrame(0.0, index=w.index, columns=w.index)
    return RiskMetrics(
        weights=w,
        sectors=sectors,
        beta=beta,
        vol=vol,
        gross=w.abs().sum() if gross is None else gross,
        net=w.sum() if net is None else net,
        corr=corr,
    )


def by_rule(alerts, rule):
    return [a for a in alerts if a.rule == rule]


def test_default_yaml_loads_and_is_valid():
    lim = load_limits(DEFAULT_LIMITS_PATH)
    assert lim.max_single_name_weight == 0.10 and lim.beta_min < lim.beta_max


def test_yaml_typo_is_rejected(tmp_path):
    cfg = yaml.safe_load(DEFAULT_LIMITS_PATH.read_text())
    cfg["max_singel_name_weight"] = 0.2
    path = tmp_path / "limits.yaml"
    path.write_text(yaml.dump(cfg))
    with pytest.raises(ValidationError):
        load_limits(path)


@pytest.mark.parametrize(
    "change",
    [
        {"beta_min": 1.0, "beta_max": 0.5},
        {"max_single_name_weight": 0},
        {"max_single_name_weight": 1.5},
        {"warn_fraction": 1.0},
        {"max_volatility": -0.1},
    ],
)
def test_invalid_limits_rejected(change):
    with pytest.raises(ValidationError):
        Limits(**{**LIMITS.model_dump(), **change})


def test_severity_boundaries():
    assert severity(0.0799, 0.10, 0.8) == OK
    assert severity(0.08, 0.10, 0.8) == WARN  # exactly 80% of the limit
    assert severity(0.10, 0.10, 0.8) == WARN  # at the limit is not yet over it
    assert severity(0.1001, 0.10, 0.8) == BREACH


def test_single_name_flags_each_offender_including_shorts():
    a = by_rule(
        evaluate(metrics({"A": 0.12, "B": -0.11, "C": 0.085, "D": 0.05}), LIMITS), "single_name"
    )
    assert [(x.detail.split()[0], x.severity) for x in a] == [
        ("A", BREACH),
        ("B", BREACH),
        ("C", WARN),
    ]


def test_single_name_ok_row_shows_worst_name():
    (a,) = by_rule(evaluate(metrics({"A": 0.05, "B": -0.06}), LIMITS), "single_name")
    assert a.severity == OK and a.detail.startswith("B ")


def test_sector_uses_net_weight():
    w = {"L": 0.40, "S": -0.40, "X": 0.05}
    sectors = {"L": "Tech", "S": "Tech", "X": "Energy"}
    (a,) = by_rule(evaluate(metrics(w, sectors), LIMITS), "sector")
    assert a.severity == OK  # 40% long and 40% short in Tech nets to 0
    over = by_rule(
        evaluate(metrics({"L": 0.20, "M": 0.15}, {"L": "Tech", "M": "Tech"}), LIMITS), "sector"
    )
    assert over[0].severity == BREACH and over[0].value == pytest.approx(0.35)


def test_unknown_sector_grouped_as_unclassified():
    a = by_rule(evaluate(metrics({"A": 0.2, "B": 0.2}, sectors={}), LIMITS), "sector")
    assert a[0].detail.startswith("Unclassified") and a[0].severity == BREACH


def test_top5_sums_five_largest_absolute_weights():
    w = {"A": 0.09, "B": -0.09, "C": 0.09, "D": 0.09, "E": 0.09, "F": 0.01}
    (a,) = by_rule(evaluate(metrics(w), LIMITS), "top5")
    assert a.value == pytest.approx(0.45) and a.severity == WARN


@pytest.mark.parametrize(
    ("beta", "expected"),
    [
        (-0.05, BREACH),
        (1.05, BREACH),
        (0.10, WARN),  # within 20% of the band width (0.2) of the lower edge
        (0.90, WARN),
        (0.50, OK),
        (0.0, WARN),  # exactly on an edge is not a breach
    ],
)
def test_beta_band(beta, expected):
    (a,) = by_rule(evaluate(metrics({"A": 0.05}, beta=beta), LIMITS), "beta")
    assert a.severity == expected
    assert a.limit_text == "0.00 to 1.00"


def test_vol_gross_and_net_rules():
    a = evaluate(metrics({"A": 0.05}, vol=0.16, gross=1.2, net=-1.1), LIMITS)
    assert by_rule(a, "volatility")[0].severity == BREACH
    assert by_rule(a, "gross")[0].severity == WARN  # 1.2 >= 0.8 * 1.5
    assert by_rule(a, "net")[0].severity == BREACH  # |-1.1| > 1.0
    assert by_rule(a, "net")[0].value == pytest.approx(1.1)


def test_correlation_only_considers_large_positions():
    idx = ["A", "B", "C"]
    corr = pd.DataFrame(0.2, index=idx, columns=idx)
    corr.loc["A", "B"] = corr.loc["B", "A"] = 0.95  # both large
    corr.loc["A", "C"] = corr.loc["C", "A"] = 0.99  # C is a 1% position: excluded
    a = by_rule(
        evaluate(metrics({"A": 0.08, "B": 0.06, "C": 0.01}, corr=corr), LIMITS), "pair_correlation"
    )
    assert [(x.detail, x.severity) for x in a] == [("A / B 0.95", BREACH)]
    assert a[0].limit_text == "0.85"


def test_correlation_rule_skipped_with_fewer_than_two_large_positions():
    assert not by_rule(evaluate(metrics({"A": 0.08, "B": 0.01}), LIMITS), "pair_correlation")


def test_every_rule_reports_and_results_are_sorted_most_severe_first():
    idx = ["A", "B"]
    alerts = evaluate(
        metrics({"A": 0.12, "B": 0.05}, corr=pd.DataFrame(0.1, index=idx, columns=idx)), LIMITS
    )
    assert {a.rule for a in alerts} == {
        "single_name",
        "sector",
        "top5",
        "beta",
        "volatility",
        "gross",
        "net",
        "pair_correlation",
    }
    order = {BREACH: 0, WARN: 1, OK: 2}
    ranks = [order[a.severity] for a in alerts]
    assert ranks == sorted(ranks) and alerts[0].severity == BREACH


def test_message_is_readable():
    a = by_rule(evaluate(metrics({"AAPL": 0.11}), LIMITS), "single_name")[0]
    assert a.message == "Single-name weight: AAPL 11.0% (limit 10.0%)"


def test_end_to_end_from_snapshot(provider):
    book = Portfolio(
        positions=[
            Position(ticker="AAA", quantity=15_000, avg_cost=90),
            Position(ticker="BBB", quantity=-3_000),
            Position(ticker="CCC", quantity=2_000),
        ],
        cash=500_000,
    )
    snap = build_snapshot(book, provider, today=date(2026, 10, 30))
    sectors = {"AAA": "Technology", "BBB": "Utilities", "CCC": "Financial Services"}
    m = metrics_from_snapshot(snap, sectors)
    assert m.beta == pytest.approx(snap.portfolio_beta) and set(m.corr.index) == set(sectors)
    alerts = evaluate(m, LIMITS)
    assert by_rule(alerts, "single_name")[0].detail.startswith("AAA")
    assert len(alerts) >= 8
