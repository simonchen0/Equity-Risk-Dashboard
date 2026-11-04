"""Save and restore the user's portfolio and settings in one local JSON file.

The file lives in the user's config directory (`~/.config/riskdash/state.json`), outside the
repo, so it is never committed. Override the location with `RISKDASH_STATE_FILE`, or turn
persistence off with `RISKDASH_PERSIST=0` (for example on a shared or public deployment,
where one file would otherwise be shared by every visitor).

Loading never raises: a missing, unreadable or partly invalid file just means "use the
defaults" for whatever could not be restored.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

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


def state_path() -> Path | None:
    """Where the state file lives, or None when persistence is switched off."""
    if os.environ.get("RISKDASH_PERSIST", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    override = os.environ.get("RISKDASH_STATE_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "riskdash" / "state.json"


def save_state(
    portfolio: Portfolio,
    limits: Limits,
    lookback: str,
    blume: bool,
    path: Path | None = None,
) -> None:
    """Write the state atomically (temp file, then rename) so a crash can't corrupt it."""
    path = path or state_path()
    if path is None:
        return
    payload = {
        "version": VERSION,
        "portfolio": portfolio.model_dump(),
        "limits": limits.model_dump(),
        "lookback": lookback,
        "blume": blume,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        os.replace(tmp, path)
    except OSError as exc:  # read-only disk etc.: the app keeps working, just unsaved
        log.warning("Could not save state to %s: %s", path, exc)


def load_state(path: Path | None = None, valid_lookbacks: tuple[str, ...] = ()) -> SavedState:
    """Read the state file. Each part is validated on its own, so one bad part does not
    discard the others. `valid_lookbacks`, if given, restricts the lookback label."""
    path = path or state_path()
    if path is None or not path.exists():
        return SavedState()
    try:
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            raise ValueError("state file is not a JSON object")
    except (OSError, ValueError) as exc:
        log.warning("Ignoring unreadable state file %s: %s", path, exc)
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
