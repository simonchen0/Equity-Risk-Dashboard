"""Evaluate a portfolio's risk metrics against its limits.

Severity: `breach` when a metric exceeds its limit, `warn` once it reaches `warn_fraction`
of the limit, otherwise `ok`. For the beta band, `warn` means within (1 - warn_fraction)
of the band's width from either edge. Rules that apply per item (names, sectors, pairs)
emit one alert per item at warn or worse, or a single `ok` alert showing the worst item.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from riskdash.alerts.limits import Limits
from riskdash.analytics.correlation import correlation_matrix
from riskdash.engine import RiskSnapshot

OK, WARN, BREACH = "ok", "warn", "breach"
SEVERITY_ORDER = {BREACH: 0, WARN: 1, OK: 2}
EPS = 1e-12  # so a value exactly at a threshold isn't missed by float noise


@dataclass(frozen=True)
class RiskMetrics:
    weights: pd.Series  # signed position weights, fraction of NAV
    sectors: Mapping[str, str]
    beta: float
    vol: float
    gross: float
    net: float
    corr: pd.DataFrame  # positions x positions


@dataclass(frozen=True)
class Alert:
    rule: str
    label: str
    severity: str
    value: float
    limit: float
    detail: str  # which item and its value, e.g. "AAPL 11.0%"
    kind: str = "pct"  # "pct" or "num": how to display value and limit
    limit_low: float | None = None  # lower bound, for the beta band

    @property
    def limit_text(self) -> str:
        if self.limit_low is not None:
            return f"{self.limit_low:.2f} to {self.limit:.2f}"
        return f"{self.limit:.1%}" if self.kind == "pct" else f"{self.limit:.2f}"

    @property
    def message(self) -> str:
        return f"{self.label}: {self.detail} (limit {self.limit_text})"


def metrics_from_snapshot(snap: RiskSnapshot, sectors: Mapping[str, str]) -> RiskMetrics:
    v = snap.valuation
    return RiskMetrics(
        weights=v.weights,
        sectors=sectors,
        beta=snap.portfolio_beta,
        vol=snap.portfolio_vol,
        gross=v.gross_exposure,
        net=v.net_exposure,
        corr=correlation_matrix(snap.returns[list(v.weights.index)]),
    )


def severity(value: float, limit: float, warn_fraction: float) -> str:
    if value > limit + EPS:
        return BREACH
    if value >= limit * warn_fraction - EPS:
        return WARN
    return OK


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _text(x: float, kind: str) -> str:
    return _pct(x) if kind == "pct" else f"{x:.2f}"


def _per_item(
    rule: str, label: str, values: pd.Series, limit: float, limits: Limits, kind: str = "pct"
) -> list[Alert]:
    """One alert per item at warn or worse; else one `ok` alert for the worst item."""
    if values.empty:
        return []
    flagged = [
        Alert(rule, label, sev, float(x), limit, f"{item} {_text(x, kind)}", kind)
        for item, x in values.sort_values(ascending=False).items()
        if (sev := severity(float(x), limit, limits.warn_fraction)) != OK
    ]
    if flagged:
        return flagged
    worst = values.idxmax()
    detail = f"{worst} {_text(values[worst], kind)}"
    return [Alert(rule, label, OK, float(values[worst]), limit, detail, kind)]


def _single(rule: str, label: str, value: float, limit: float, limits: Limits) -> Alert:
    sev = severity(value, limit, limits.warn_fraction)
    return Alert(rule, label, sev, value, limit, _pct(value))


def _beta_alert(beta: float, limits: Limits) -> Alert:
    lo, hi = limits.beta_min, limits.beta_max
    margin = (1 - limits.warn_fraction) * (hi - lo)
    if beta < lo - EPS or beta > hi + EPS:
        sev = BREACH
    elif beta < lo + margin - EPS or beta > hi - margin + EPS:
        sev = WARN
    else:
        sev = OK
    return Alert("beta", "Portfolio beta", sev, beta, hi, f"{beta:.2f}", "num", limit_low=lo)


def _correlation_alerts(m: RiskMetrics, limits: Limits) -> list[Alert]:
    large = [t for t in m.weights.index if abs(m.weights[t]) >= limits.correlation_min_weight]
    if len(large) < 2:
        return []
    sub = m.corr.loc[large, large]
    mask = np.triu(np.ones(sub.shape, dtype=bool), k=1)
    pairs = sub.where(mask).stack()
    pairs.index = [f"{a} / {b}" for a, b in pairs.index]
    return _per_item(
        "pair_correlation", "Pair correlation", pairs, limits.max_pair_correlation, limits, "num"
    )


def evaluate(m: RiskMetrics, limits: Limits) -> list[Alert]:
    """All alerts, most severe first. Every rule appears at least once (as `ok` if clear)."""
    abs_w = m.weights.abs()
    sector_net = m.weights.groupby(lambda t: m.sectors.get(t) or "Unclassified").sum().abs()
    top5 = float(abs_w.nlargest(5).sum())

    alerts = [
        *_per_item(
            "single_name", "Single-name weight", abs_w, limits.max_single_name_weight, limits
        ),
        *_per_item("sector", "Sector net weight", sector_net, limits.max_sector_net_weight, limits),
        _single("top5", "Top-5 concentration", top5, limits.max_top5_weight, limits),
        _beta_alert(m.beta, limits),
        _single("volatility", "Portfolio volatility", m.vol, limits.max_volatility, limits),
        _single("gross", "Gross exposure", m.gross, limits.max_gross_exposure, limits),
        _single("net", "Net exposure", abs(m.net), limits.max_abs_net_exposure, limits),
        *_correlation_alerts(m, limits),
    ]
    return sorted(alerts, key=lambda a: SEVERITY_ORDER[a.severity])
