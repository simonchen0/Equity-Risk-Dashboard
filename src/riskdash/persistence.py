"""Serialize the user's portfolio and settings to one JSON string and back.

The app keeps that string in the visitor's own browser (localStorage), so each visitor has a
private copy that survives a page refresh, on a public deployment as well as locally.
This module only converts; where the string is stored is the UI layer's job.

Loading never raises: a missing, unreadable or partly invalid string just means "use the
defaults" for whatever could not be restored.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from riskdash.alerts.limits import Limits
from riskdash.portfolio.models import Portfolio

log = logging.getLogger(__name__)

VERSION = 1


@dataclass(frozen=True)
class SavedState:
    """Whatever could be restored; `None` means "not saved or not valid: use the default"."""

    portfolio: Portfolio | None = None
    limits: Limits | None = None
    lookback: str | None = None
    blume: bool | None = None


def dump_state(portfolio: Portfolio, limits: Limits, lookback: str, blume: bool) -> str:
    return json.dumps(
        {
            "version": VERSION,
            "portfolio": portfolio.model_dump(),
            "limits": limits.model_dump(),
            "lookback": lookback,
            "blume": blume,
        }
    )


def parse_state(text: str | None, valid_lookbacks: tuple[str, ...] = ()) -> SavedState:
    """Read a string made by `dump_state`. Each part is validated on its own, so one bad part
    does not discard the others. `valid_lookbacks`, if given, restricts the lookback label."""
    if not text:
        return SavedState()
    try:
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("saved state is not a JSON object")
    except ValueError as exc:
        log.warning("Ignoring unreadable saved state: %s", exc)
        return SavedState()

    portfolio = _parse(Portfolio, raw.get("portfolio"), "portfolio")
    limits = _parse(Limits, raw.get("limits"), "limits")
    lookback = raw.get("lookback")
    if not isinstance(lookback, str) or (valid_lookbacks and lookback not in valid_lookbacks):
        lookback = None
    blume = raw.get("blume")
    return SavedState(portfolio, limits, lookback, blume if isinstance(blume, bool) else None)


def _parse(model, data, name: str):
    if data is None:
        return None
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        log.warning("Ignoring invalid saved %s: %s", name, exc)
        return None
